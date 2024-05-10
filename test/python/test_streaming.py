"""
Script to test the proxy's ability to support response streaming.

Tested with openai package version 1.12.0.
"""

from openai import AzureOpenAI
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk

client = AzureOpenAI(
    azure_endpoint="http://localhost",
    api_version="2024-02-01",
    api_key="72bd81ef32763530b29e3da63d46ad6",
)

deployment_name = "gpt-4-turbo"

response = client.chat.completions.create(
    model=deployment_name,
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
