"""
Tests if PowerProxy is running.
"""

import argparse

import requests

parser = argparse.ArgumentParser()
parser.add_argument(
    "--powerproxy-endpoint", type=str, default="http://localhost", help="Path to PowerProxy/Azure OpenAI endpoint"
)
args, unknown = parser.parse_known_args()


# do a liveness check to ensure that PowerProxy is running
print("Checking if PowerProxy is up and running...")
try:
    response = requests.get(f"{args.powerproxy_endpoint}/powerproxy/health/liveness", timeout=None)
    assert response.status_code == 204
except Exception as exception:
    raise Exception(  # pylint: disable=broad-exception-raised
        (
            "Could not connect to PowerProxy. Is it up and running? PowerProxy needs to be started before running the"
            "tests."
        )
    ) from exception
