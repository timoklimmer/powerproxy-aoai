"""
Script to test the proxy's ability to support response streaming.

Tested with openai package version 1.35.10.
"""

# pylint: disable=line-too-long

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
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Describe this picture:"},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": """data:image/jpeg;base64,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
EREBERAREQEREBERAREQP//Z""",
                        "detail": "high",
                    },
                },
            ],
        },
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
