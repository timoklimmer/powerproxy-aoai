"""Script to test the proxy's ability to support response streaming."""

from openai import AzureOpenAI
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk

client = AzureOpenAI(
    azure_endpoint="http://localhost",
    api_version="2023-03-15-preview",
    api_key="72bd81ef32763530b29e3da63d46ad6",
)

response = client.chat.completions.create(
    model="gpt-35-turbo",
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
    stream=True,
)

# pylint: disable=not-an-iterable
for chunk in response:
    # pylint: enable=not-an-iterable
    chunk: ChatCompletionChunk
    if len(chunk.choices) > 0:
        choice = chunk.choices[0]
        if choice.finish_reason != "stop" and choice.delta and choice.delta.content:
            print(choice.delta.content, end="", flush=True)
