"""
Script to test the proxy's ability to support response streaming.

Tested with openai package version 1.35.10.
"""

import argparse

from openai import AzureOpenAI
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk

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

client = AzureOpenAI(
    azure_endpoint=args.powerproxy_endpoint,
    api_version=args.api_version,
    api_key=args.api_key,
)

response = client.chat.completions.create(
    model=args.deployment_name,
    messages=[
        {
            "role": "system",
            "content": "You are an AI assistant that helps people find information.",
        },
        {"role": "user", "content": "Tell me a very long joke!"},
    ],
    temperature=0,
    max_tokens=800,
    top_p=0.95,
    frequency_penalty=0,
    presence_penalty=0,
    stop=None,
    stream=True,
)

for chunk in response:
    chunk: ChatCompletionChunk
    if len(chunk.choices) > 0:
        choice = chunk.choices[0]
        if choice.finish_reason != "stop" and choice.delta and choice.delta.content:
            print(choice.delta.content, end="", flush=True)

print()
