"""
PowerProxy for AOAI - reverse proxy to process requests and responses to/from Azure Open AI.

- Use the "Debug powershell.py" launch configuration in VS.Code to develop and debug this script.
- Adjust the launch configuration in VS.Code as needed (esp. for plugins enabled)
"""

import argparse
import asyncio
import datetime
import io
import json
import random
import time
from contextlib import asynccontextmanager
from datetime import datetime

import httpx
import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.responses import Response, StreamingResponse
from helpers.config import Configuration
from helpers.header import print_header
from plugins.base import ImmediateResponseException, foreach_plugin
from version import VERSION

## define script arguments
parser = argparse.ArgumentParser()
# --config-file
parser.add_argument(
    "--config-file",
    type=str,
    help="Path to config file",
)
# --config-env-var
parser.add_argument(
    "--config-env-var",
    type=str,
    help="Name of the environment variable containing the configuration as JSON string.",
)
# --port
parser.add_argument(
    "--port",
    type=int,
    default=80,
    help=(
        "Port where the proxy runs. Ports <= 1024 may need special permissions in Linux. "
        "Default: 80."
    ),
)
args, unknown = parser.parse_known_args()

## load configuration
config = Configuration.from_args(args)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan function for FastAPI."""

    # startup
    # print header and config values
    print_header(f"PowerProxy for Azure OpenAI - v{VERSION}")
    Configuration.print_setting("Proxy runs at port", args.port)
    config.print()
    foreach_plugin(config.plugins, "on_print_configuration")

    # collect AOAI endpoints and corresponding clients
    app.state.aoai_endpoints = {}
    if config.get("aoai/mock_response"):

        async def get_mock_response(request):
            ms_to_wait_before_return = config.get("aoai/mock_response/ms_to_wait_before_return")
            if ms_to_wait_before_return:
                ms_to_wait_before_return = float(ms_to_wait_before_return)
                await asyncio.sleep(ms_to_wait_before_return / 1_000)
            return httpx.Response(200, json=config.get("aoai/mock_response/json"))

        app.state.aoai_endpoints["mock"] = {
            "Mock client": {
                "url": "",
                "key": "",
                "client": httpx.AsyncClient(
                    base_url="https://mock/",
                    transport=httpx.MockTransport(get_mock_response),
                ),
                "next_request_not_before_timestamp_ms": 0,
                "non_streaming_fraction": 1,
            }
        }
    else:
        app.state.aoai_endpoints = {
            endpoint["name"]: {
                "url": endpoint["url"],
                "key": endpoint["key"],
                "client": httpx.AsyncClient(base_url=endpoint["url"]),
                "next_request_not_before_timestamp_ms": 0,
                "non_streaming_fraction": float(endpoint["non_streaming_fraction"]),
            }
            for endpoint in config["aoai/endpoints"]
        }
    if len(app.state.aoai_endpoints) == 0:
        raise ValueError(
            (
                "Missing endpoints for Azure OpenAI. Ensure that at least one endpoint for Azure "
                "OpenAI or a mock response is configured in PowerProxy's configuration."
            )
        )

    # print serve notification
    print()
    print("Serving incoming requests...")
    print()

    # run the app
    yield

    # shutdown
    # close AOAI endpoint connections
    for aoai_endpoint_name in app.state.aoai_endpoints:
        await app.state.aoai_endpoints[aoai_endpoint_name].aclose()


## define and run proxy app
app = FastAPI(lifespan=lifespan)


@app.exception_handler(ImmediateResponseException)
async def exception_callback(request: Request, exception: ImmediateResponseException):
    """Immediately return given response when an ImmediateResponseException is raised."""
    return exception.response


# liveness probe
@app.get(
    "/powerproxy/health/liveness",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Liveness probe for the PowerProxy",
)
async def liveness_probe():
    """
    Return a 204/No Content if the container is live.
    Note: This is required by some hosting services to know if there are issues with the container.
    """
    return None


# all other GETs and POSTs
@app.get("/{path:path}")
@app.post("/{path:path}")
async def handle_request(request: Request, path: str):
    """Handle any incoming request."""
    # create a new routing slip, populate it with some variables and tell plugins about new request
    routing_slip = {
        "request_received_utc": datetime.utcnow(),
        "incoming_request": request,
        "incoming_request_body": await request.body(),
    }
    routing_slip["incoming_request_body_dict"] = None
    try:
        routing_slip["incoming_request_body_dict"] = await request.json()
    except:
        pass
    routing_slip["is_non_streaming_response_requested"] = not (
        "stream" in routing_slip["incoming_request_body_dict"]
        and str(routing_slip["incoming_request_body_dict"]["stream"]).lower() == "true"
    )
    foreach_plugin(config.plugins, "on_new_request_received", routing_slip)

    # identify client
    # notes: - When API authentication is used, we get an API key in header 'api-key'. This
    #          would usually be the API key for Azure Open AI, but we configure and use
    #          client-specific keys here for the proxy to identify the client. We will replace the
    #          API key against the real AOAI key later.
    #        - For Azure AD authentication, we should get no API key but an Azure AD token in
    #          header 'Authorization'. Unfortunately, we cannot interpret or modify that token,
    #          so we need another mechanism to identify clients. In that case, we need a
    #          separate instance of PowerProxy for each client, whereby each client uses a fixed
    #          client.
    #        - Some requests may neither contain an API key or an Azure AD token. In that case,
    #          we need to make sure that the proxy continues to work.
    headers = {
        key: request.headers[key]
        for key in set(request.headers.keys())
        - {"Host", "host", "Content-Length", "content-length"}
    }
    client = None
    if config["FIXED_CLIENT"]:
        client = config["FIXED_CLIENT"]
    if "api-key" in headers:
        if headers["api-key"] not in config.key_client_map:
            raise ValueError(
                (
                    "The provided API key is not a valid PowerProxy key. Ensure that the "
                    "'api-key' header contains valid API key from the PowerProxy's "
                    "configuration."
                )
            )
        client = config.key_client_map[headers["api-key"]] if client is None else client
    routing_slip["client"] = client
    if client:
        foreach_plugin(config.plugins, "on_client_identified", routing_slip)

    # get response from AOAI by iterating through the configured endpoints
    aoai_response: httpx.Response = None
    for aoai_endpoint_name in app.state.aoai_endpoints:
        aoai_endpoint = app.state.aoai_endpoints[aoai_endpoint_name]

        # try next endpoint if this endpoint is blocked
        if aoai_endpoint["next_request_not_before_timestamp_ms"] > get_current_timestamp_in_ms():
            continue

        # try next endpoint if we have a non-streaming request and if we want to skip it to reserve
        # resources for streaming requests
        if (
            routing_slip["is_non_streaming_response_requested"]
            and (
                aoai_endpoint["non_streaming_fraction"] == 0
                or random.random() > aoai_endpoint["non_streaming_fraction"]
            )
            and aoai_endpoint["non_streaming_fraction"] != 1
        ):
            continue

        # replace API key against real API key from AOAI
        headers["api-key"] = aoai_endpoint["key"] or ""

        # remember endpoint and request start time
        routing_slip["aoai_endpoint_name"] = aoai_endpoint_name
        routing_slip["aoai_request_start_time"] = get_current_timestamp_in_ms()

        # send request
        new_timeout = httpx.Timeout(timeout=5.0)
        new_timeout.read = 120.0
        aoai_request = aoai_endpoint["client"].build_request(
            request.method,
            path,
            timeout=new_timeout,
            params=request.query_params,
            headers=headers,
            content=routing_slip["incoming_request_body"],
        )
        aoai_response = await aoai_endpoint["client"].send(
            aoai_request,
            stream=(not routing_slip["is_non_streaming_response_requested"]),
        )
        if aoai_response.status_code == 429:
            # got 429
            # block endpoint for some time, either according to the time given by AOAI or, if not
            # available, for 10 seconds
            waiting_time_ms_until_next_request = (
                int(aoai_response.headers["retry-after-ms"])
                if "retry-after-ms" in aoai_response.headers
                else 10_000
            )
            aoai_endpoint["next_request_not_before_timestamp_ms"] = (
                get_current_timestamp_in_ms() + waiting_time_ms_until_next_request
            )
            # try next endpoint
            continue

        # if we reached here, we found an endpoint which is able to serve our request
        # -> go ahead
        break

    # raise 429 if we could not find any endpoint suitable endpoint
    if aoai_response is None:
        raise ImmediateResponseException(
            Response(
                content="Could not find any endpoint with remaining capacity. Try again later.",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        )

    # process received headers
    routing_slip["headers_from_target"] = aoai_response.headers
    foreach_plugin(config.plugins, "on_headers_from_target_received", routing_slip)

    # determine if it's actually an event stream or not
    routing_slip["is_event_stream"] = (
        "content-type" in aoai_response.headers
        and aoai_response.headers["content-type"] == "text/event-stream"
    )

    # return different response types depending if it's an event stream or not
    routing_slip["response_headers_from_target"] = {
        header_item[0].decode(): header_item[1].decode()
        for header_item in aoai_response.headers.raw
    }
    match routing_slip["is_event_stream"]:
        case False:
            # non-streamed response
            body = await aoai_response.aread()
            measure_aoai_roundtrip_time_ms(routing_slip)
            try:
                routing_slip["body_dict_from_target"] = json.load(io.BytesIO(body))
                foreach_plugin(config.plugins, "on_body_dict_from_target_available", routing_slip)
            except:
                # eat any exception in case the response cannot be parsed
                pass
            return Response(
                content=body,
                status_code=aoai_response.status_code,
                headers=routing_slip["response_headers_from_target"],
            )
        case True:
            # event stream
            # forward and process events as they come in
            # note: see https://learn.microsoft.com/de-de/azure/ai-services/openai/reference
            async def yield_data_events():
                """Stream response while invoking plugins."""
                async for line in aoai_response.aiter_lines():
                    yield f"{line}\r\n"
                    routing_slip["data_from_target"] = None
                    if line.startswith("data: "):
                        data = line[6:]
                        if data != "[DONE]":
                            routing_slip["data_from_target"] = data
                            foreach_plugin(
                                config.plugins,
                                "on_data_event_from_target_received",
                                routing_slip,
                            )
                measure_aoai_roundtrip_time_ms(routing_slip)
                foreach_plugin(
                    config.plugins, "on_end_of_target_response_stream_reached", routing_slip
                )

            return StreamingResponse(
                yield_data_events(),
                status_code=aoai_response.status_code,
                headers=routing_slip["response_headers_from_target"],
            )


def get_current_timestamp_in_ms():
    """Return the current timestamp in millisecond resolution."""
    return time.time_ns() // 1_000_000


def measure_aoai_roundtrip_time_ms(routing_slip):
    """Measure the roundtrip time from/to Azure OpenAI endpoint."""
    routing_slip["aoai_request_end_time"] = get_current_timestamp_in_ms()
    routing_slip["aoai_roundtrip_time_ms"] = int(
        routing_slip["aoai_request_end_time"] - routing_slip["aoai_request_start_time"]
    )


if __name__ == "__main__":
    # note: this applies only when the powerproxy.py script is executed directly. In the Dockerfile
    #       provided, we use a uvicorn command to run the app, so parameters might need to be
    #       modified there AS WELL.
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(args.port),
        log_level="warning",
        server_header=False,
        date_header=False,
        proxy_headers=False,
        timeout_keep_alive=120,
        timeout_graceful_shutdown=120,
    )
