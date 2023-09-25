"""Script to test the proxy's support for requests responding with a one-time response."""

import openai

openai.api_type = "azure"
openai.api_base = "http://localhost"
openai.api_version = "2023-03-15-preview"
openai.api_key = "98ef51ae30342978f81c4ad96ce47ab"

response = openai.ChatCompletion.create(
    engine="gpt-35-turbo",
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

print(response)

print("")
