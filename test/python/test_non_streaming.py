"""Script to test the proxy's support for requests responding with a one-time response."""

from openai import AzureOpenAI

client = AzureOpenAI(
    azure_endpoint="http://localhost",
    api_version="2023-03-15-preview",
    api_key="04ae14bc78184621d37f1ce57a52eb7",
)

chat_completions_request = client.chat.completions.create(
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
    stream=False,
)

print(chat_completions_request.choices[0].message.content)
