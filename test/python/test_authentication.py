"""
Several tests to see if the authentication works as intended.

Note: Some tests involve an Entra ID authentication. Before running the tests, either make sure the user running these
      tests has appropriate permissions on the Azure OpenAI endpoint or comment out the respective tests.

      Owner or Contributor role is not sufficient. You will need something like a "Cognitive Services OpenAI User" role.
      It can take several minutes until new permissions come into effect.

      Besides

      See https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/role-based-access-control for details.
"""

import argparse
import json

import requests
from azure.identity import DefaultAzureCredential

parser = argparse.ArgumentParser()
parser.add_argument(
    "--powerproxy-endpoint", type=str, default="http://localhost", help="Path to PowerProxy/Azure OpenAI endpoint"
)
parser.add_argument(
    "--api-key", type=str, default="04ae14bc78184621d37f1ce57a52eb7", help="API key to access PowerProxy"
)
parser.add_argument("--deployment-name", type=str, default="gpt-4o", help="Name of Azure OpenAI deployment to test")
parser.add_argument(
    "--api-version", type=str, default="2024-06-01", help="API version to use when accessing Azure OpenAI"
)
args, unknown = parser.parse_known_args()


def send_post_request(api_key=None, authorization_token=None):
    """
    Sends a POST request to Azure OpenAI using the given API key and/or authorization token. Header field is omitted
    if none.
    """
    headers = {
        "Content-Type": "application/json",
        "Connection": "keep-alive",
        "Accept-Encoding": "gzip, deflate",
        "Accept": "*/*",
    }
    if api_key:
        headers = headers | {"api-key": api_key}
    if authorization_token:
        headers = headers | {"Authorization": f"Bearer {authorization_token}"}

    return requests.post(
        (
            f"{args.powerproxy_endpoint}/openai/deployments/{args.deployment_name}/chat/completions"
            f"?api-version={args.api_version}"
        ),
        headers=headers,
        data=json.dumps(
            {
                "messages": [
                    {"role": "system", "content": "You are an AI assistant that helps people find information."},
                    {"role": "user", "content": "Tell me a joke!"},
                ],
                "temperature": 0,
                "max_tokens": 800,
                "top_p": 0.95,
                "frequency_penalty": 0,
                "presence_penalty": 0,
                "stop": None,
                "stream": False,
            }
        ),
        timeout=None,
    )


# regular API key authentication
print("Testing regular API key authentication...")
response = send_post_request(api_key=args.api_key)
assert response.status_code == 200

# wrong API key
# note: the key below should not be configured in PowerProxy's config
print("Testing wrong API key authentication...")
response = send_post_request(api_key="71ae12bc78184621d37f13e57a52eb9")
assert response.status_code == 401

# neither API key nor authentication token
# note: the key below should not be configured in PowerProxy's config
print("Testing neither API key nor token request...")
response = send_post_request()
assert response.status_code == 401

# regular Entra ID/Azure AD authentication
# note: this needs a proper setup of permissions, see above for details
print(
    (
        "Testing regular Entra ID/Azure AD authentication (ensure you have correct permissions before running this test"
        ")..."
    )
)
response = send_post_request(
    authorization_token=DefaultAzureCredential().get_token("https://cognitiveservices.azure.com/.default").token
)
assert response.status_code == 200

# same API key and Bearer token
# note: some openai package versions use this
print("Testing regular API key and same API key in Authorization: Bearer...")
response = send_post_request(api_key=args.api_key, authorization_token=args.api_key)
assert response.status_code == 200

# wrong authentication token
print("Testing wrong Entra ID/Azure AD authentication...")
response = send_post_request(authorization_token="ThisShouldBreakByIntention")
assert response.status_code == 401
