"""
Script to test the proxy's ability to support response streaming when functions are used.

Tested with openai package version 1.12.0.
"""

import json

from openai import AzureOpenAI

client = AzureOpenAI(
    azure_endpoint="http://localhost",
    api_version="2024-02-01",
    api_key="72bd81ef32763530b29e3da63d46ad6",
)

deployment_name = "gpt-4-turbo"

function_name = ""
arguments = ""
for chunk in client.chat.completions.create(
    model=deployment_name,
    messages=[
        {
            "role": "user",
            # "content": "Find beachfront hotels in San Diego for less than $300 a month with free breakfast.",
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
    stream=True,
):
    if "ChoiceDeltaToolCallFunction" in f"{chunk}":
        function_name += chunk.choices[0].delta.tool_calls[0].function.name or ""
        arguments += chunk.choices[0].delta.tool_calls[0].function.arguments or ""


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


print(f"Function Name: {function_name}")
print(f"Arguments: {arguments}")

match function_name:
    case "search_hotels":
        search_hotels(**(json.loads(arguments)))
    case "book_hotel":
        book_hotel(**(json.loads(arguments)))
    case _:
        raise ValueError(f"Function name '{function_name}' is not available.")
