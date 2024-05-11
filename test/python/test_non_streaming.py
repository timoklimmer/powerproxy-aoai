"""
Script to test the proxy's support for requests responding with a one-time response.

Tested with openai package version 1.28.0.
"""

import argparse

from openai import AzureOpenAI

parser = argparse.ArgumentParser()
parser.add_argument(
    "--powerproxy-endpoint", type=str, default="http://localhost", help="Path to PowerProxy/Azure OpenAI endpoint"
)
parser.add_argument(
    "--api-key", type=str, default="04ae14bc78184621d37f1ce57a52eb7", help="API key to access PowerProxy"
)
parser.add_argument(
    "--deployment-name", type=str, default="gpt-4-turbo", help="Name of Azure OpenAI deployment to test"
)
parser.add_argument(
    "--api-version", type=str, default="2024-02-01", help="API version to use when accessing Azure OpenAI"
)
args, unknown = parser.parse_known_args()

client = AzureOpenAI(azure_endpoint=args.powerproxy_endpoint, api_version=args.api_version, api_key=args.api_key)

response = client.chat.completions.create(
    model=args.deployment_name,
    messages=[
        {
            "role": "system",
            "content": "You are an AI assistant that helps people find information.",
        },
        {"role": "user", "content": "Tell me a joke!"},
        {
            "role": "assistant",
            "content": "Why did the tomato turn red? Because it saw the salad dressing!",
        },
        {"role": "user", "content": "Yeah, that's a great one."},
    ],
    temperature=0,
    max_tokens=800,
    top_p=0.95,
    frequency_penalty=0,
    presence_penalty=0,
    stop=None,
    stream=False,
)

print(response.choices[0].message.content)
