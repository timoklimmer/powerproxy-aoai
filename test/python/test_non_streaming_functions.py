"""
Script to test the proxy's ability to support response streaming when functions are used.

Tested with openai package version 1.12.0.
"""

# pylint: disable=not-an-iterable, duplicate-key

import json
from openai import AzureOpenAI

client = AzureOpenAI(
    azure_endpoint="http://localhost",
    api_version="2024-02-01",
    api_key="04ae14bc78184621d37f1ce57a52eb7",
)

deployment_name = "gpt-4-turbo"

function_name = ""
arguments = ""
response = client.chat.completions.create(
    model=deployment_name,
    messages=[
        {
            "role": "user",
            "content": "Book Palace Beach, starting Feb 14 to Feb 18.",
        }
    ],
    tools=[
        {
            "type": "function",
            "function": {
                "name": "search_hotels",
                "description": "Retrieves hotels from the search index based on the parameters provided.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The location of the hotel (i.e. Seattle, WA)",
                        },
                        "max_price": {
                            "type": "number",
                            "description": "The maximum price for the hotel",
                        },
                        "features": {
                            "type": "string",
                            "description": "A comma separated list of features (i.e. beachfront, free wifi, etc.)",
                        },
                    },
                    "required": ["location"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "book_hotel",
                "description": "Books a hotel based on the parameters provided.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "The name of the hotel (i.e. Palace Beach)",
                        },
                        "start_date": {
                            "type": "string",
                            "description": "The start date of the booking.",
                        },
                        "end_date": {
                            "type": "string",
                            "description": "The end date of the booking.",
                        },
                    },
                    "required": ["name", "start_date", "end_date"],
                },
            },
        },
    ],
    temperature=0,
    tool_choice="auto",
    stream=False,
)


def search_hotels(location, max_price, features):
    """Searches for hotels."""
    print(
        f"Searching hotels in {location} with max price {max_price} and {features}..."
    )
    print("TODO: Complete -- this function is only for demo purposes.")


def book_hotel(name, start_date, end_date):
    """Books a hotel."""
    print(f"Booking hotel '{name}'. Start date: {start_date}, End date: {end_date}...")
    print("TODO: Complete -- this function is only for demo purposes.")


for choice in response.choices:
    if choice.finish_reason != "stop" and choice.message.tool_calls:
        for tool_call in choice.message.tool_calls:
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
        if function_name == "search_hotels":
            search_hotels(**arguments)
        elif function_name == "book_hotel":
            book_hotel(**arguments)
        else:
            raise ValueError(f"Function name '{function_name}' is not available.")
