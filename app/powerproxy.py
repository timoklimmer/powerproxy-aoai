"""
PowerProxy for AOAI - reverse proxy to process requests and responses to/from Azure Open AI.

- Use the "Debug powershell.py" launch configuration in VS.Code to develop and debug this script.
- Adjust the launch configuration in VS.Code as needed (esp. for plugins enabled)
"""

# pylint: disable=invalid-name, import-error

import io
import json

import httpx
import uvicorn
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.responses import Response, StreamingResponse
from helpers.config import get_config
from helpers.logger import build_logger
from plugins.base import foreach_plugin
from version import VERSION
from tenacity import (
    retry_if_exception_type,
    retry,
    stop_after_attempt,
    wait_random_exponential,
)

# misc
_logger = build_logger(__name__)
PORT = get_config('port', validate=int, default=80)
OPENAI_HEADER_AUTH_NAME = "api-key"

# define and run proxy app
app = FastAPI()


# app startup event
@app.on_event("startup")
async def startup_event():
    """Invoked when the app is started."""
    # print header and config values
    _logger.info(f"PowerProxy for Azure OpenAI - v{VERSION}")
    _logger.debug(f"Proxy port: {PORT}")

    # instantiate HTTP client for AOAI endpoint
    app.state.target_client: httpx.AsyncClient = httpx.AsyncClient(
        base_url=get_config("endpoint", sections="aoai", validate=str, required=True)
    )

    # print serve notification
    _logger.info("Serving incoming requests...")


# app shutdown
@app.on_event("shutdown")
async def shutdown_event():
    """Invoked when the app is shut down."""
    await app.state.target_client.aclose()


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
    # create a new routing slip and tell plugins about new request
    routing_slip = {
        "incoming_request": request,
        "incoming_request_body": await request.body(),
    }
    foreach_plugin("on_new_request_received", routing_slip)

    # identify client and replace API key if needed
    # notes: - When API authentication is used, we get an API key in header 'api-key'. This would
    #          usually be the API key for Azure Open AI, but we configure and use client-specific
    #          keys here for the proxy to identify the client and replace the API key against the
    #          real AOAI key afterwards.
    #        - For Azure AD authentication, we should get no API key but an Azure AD token in header
    #          'Authorization'. Unfortunately, we cannot interpret or modify that token, so we need
    #          another mechanism to identify clients. In that case, we need a separate instance of
    #          PowerProxy for each client, whereby each client uses a fixed client.
    #        - Some requests may neither contain an API key or an Azure AD token. In that case, we
    #          need to make sure that the proxy continues to work.
    headers = {
        key: request.headers[key]
        for key in set(request.headers.keys())
        - {"Host", "host", "Content-Length", "content-length"}
    }

    fixed_client = get_config("FIXED_CLIENT", validate=str)
    client = fixed_client if fixed_client else None

    if OPENAI_HEADER_AUTH_NAME not in headers:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f'No provided API key. Ensure that the "{OPENAI_HEADER_AUTH_NAME}" header contains valid API key.',
        )

    client_map = dict(
        (client.get("key"), client.get("name"))
        for client in get_config("clients", validate=list, required=True)
    )
    if headers[OPENAI_HEADER_AUTH_NAME] not in client_map:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f'The provided API key is not a valid PowerProxy key. Ensure that the "{OPENAI_HEADER_AUTH_NAME}" header contains valid API key.',
        )
    client = client_map[headers[OPENAI_HEADER_AUTH_NAME]] if client is None else client
    headers[OPENAI_HEADER_AUTH_NAME] = get_config("key", sections="aoai", validate=str, required=True)

    _logger.debug(f"Identified client: {client}")
    routing_slip["client"] = client
    foreach_plugin("on_client_identified", routing_slip)

    # forward request to target endpoint and get response
    _logger.debug(f"Forwarded headers: {headers}")
    aoai_response = await _send_to_openai(
        request.method,
        path,
        request.query_params,
        headers,
        routing_slip["incoming_request_body"],
    )

    routing_slip["headers_from_target"] = aoai_response.headers
    foreach_plugin("on_headers_from_target_received", routing_slip)

    # determine if it's an event stream or not
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
            try:
                routing_slip["body_dict_from_target"] = json.load(io.BytesIO(body))
                foreach_plugin("on_body_dict_from_target_available", routing_slip)
            # pylint: disable=bare-except
            except:
                # eat any exception in case the response cannot be parsed
                pass
            # pylint: enable=bare-except
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
                                "on_data_event_from_target_received", routing_slip
                            )

                foreach_plugin(
                    "on_end_of_target_response_stream_reached", routing_slip
                )

            return StreamingResponse(
                yield_data_events(),
                status_code=aoai_response.status_code,
                headers=routing_slip["response_headers_from_target"],
            )


@retry(
    reraise=True,
    retry=retry_if_exception_type(
        (httpx.NetworkError, httpx.RemoteProtocolError, httpx.DecodingError)
    ),
    stop=stop_after_attempt(3),
    wait=wait_random_exponential(multiplier=0.5, max=30),
)
async def _send_to_openai(method, path, params, headers, content) -> httpx.Response:
    try:
        return await app.state.target_client.request(
            method,
            path,
            content=content,
            follow_redirects=False,
            headers=headers,
            params=params,
            timeout=60,
        )
    except httpx.TimeoutException:
        _logger.error(
            "OpenAI backend does not respond on time. Make sure network connection between PowerProxy and Azure OpenAI works properly, then investigate on Azure OpenAI API."
        )
        raise HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT)
    except httpx.ConnectError:
        _logger.error(
            "OpenAI backend does not respond. Make sure the URL is properly configured, then investigate on Azure OpenAI API.",
            exc_info=True,
        )
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)


if __name__ == "__main__":
    # This applies only when the powerproxy.py script is executed directly. In the Dockerfile provided, we use a uvicorn command to run the app, so parameters might need to be modified there AS WELL.
    #
    # Note about headers:
    # - We do need those related to proxy (param named "proxy_headers"), in the case the app is ran in a container behind a reverse proxy, like Traefik, Nginx, etc.
    # - We do need those related to date (param named "date_header"), as we want to be able to see the date of the request in the monitoring, and the customer able to calculate the latency plus cache the response.
    # - We do not need those related to server (param named "server_header"), as we do not want to expose the fact that we are using FastAPI or Uvicorn, this is a security measure.
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
        log_level="warning",
        server_header=False,
        date_header=True,
        proxy_headers=True,
        timeout_keep_alive=120,
        timeout_graceful_shutdown=120,
    )
