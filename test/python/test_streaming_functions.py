#!/usr/bin/env python
"""
Script to test the proxy's ability to support response streaming when functions are used.

Tested with openai package version 1.12.0.
"""

from openai import AzureOpenAI
import json

client = AzureOpenAI(
    azure_endpoint="http://localhost",
    api_version="2024-02-01",
    api_key="72bd81ef32763530b29e3da63d46ad6",
)


def search_hotels(location, max_price, features):
    print(
        f"PRINT STATEMENT: searching hotels in {location} with {max_price} and {features}"
    )  # Clairfication that the function actually is running and the model isn't making stuff up.
    if location == "San Diego":
        return json.dumps(
            [
                {
                    "name": "Hotel 1",
                    "price": 200,
                    "features": ["beachfront", "free breakfast"],
                },
                {
                    "name": "Hotel 2",
                    "price": 250,
                    "features": ["beachfront", "free breakfast"],
                },
            ]
        )
    else:
        return json.dumps({"location": location, "temperature": "unknown"})


def run_conversation():
    messages = [
        {
            "role": "user",
            "content": "Tell me a funny joke and also find beachfront hotels in San Diego for less than $300 a month with free breakfast.",
        }
    ]
    tools = [
        {
            "type": "function",
            "function": {
                "name": "search_hotels",
                "description": "Retrieves hotels from the search index based on the parameters provided",
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
        }
    ]

    stream = client.chat.completions.create(
        model="gpt4-turbo",
        messages=messages,
        tools=tools,
        temperature=0,
        tool_choice="auto",
        stream=True,
    )

    available_functions = {
        "search_hotels": search_hotels,
        # "add_another_function_here": add_another_function_here,
    }
    response_text = ""
    tool_calls = []

    for chunk in stream:

        if len(chunk.choices) == 0:
            print("choices is empty")
            continue

        if chunk.choices[0].delta:
            print(chunk.choices)
            delta = chunk.choices[0].delta

        if delta and delta.content:
            # content chunk -- send to browser and record for later saving
            print(delta.content)
            response_text += delta.content

        elif delta and delta.tool_calls:
            tcchunklist = delta.tool_calls
            for tcchunk in tcchunklist:
                if len(tool_calls) <= tcchunk.index:
                    tool_calls.append(
                        {
                            "id": "",
                            "type": "function",
                            "function": {"name": "", "arguments": ""},
                        }
                    )
                tc = tool_calls[tcchunk.index]

                if tcchunk.id:
                    tc["id"] += tcchunk.id
                if tcchunk.function.name:
                    tc["function"]["name"] += tcchunk.function.name
                if tcchunk.function.arguments:
                    tc["function"]["arguments"] += tcchunk.function.arguments

    # print(tool_calls)

    messages.append(
        {
            "tool_calls": tool_calls,
            "role": "assistant",
        }
    )

    for tool_call in tool_calls:

        function_name = tool_call["function"]["name"]
        function_to_call = available_functions[function_name]
        function_args = json.loads(tool_call["function"]["arguments"])
        function_response = function_to_call(
            location=function_args.get("location"),
            max_price=function_args.get("max_price"),
            features=function_args.get("features"),
            # unit=function_args.get("unit"),
        )

        messages.append(
            {
                "tool_call_id": tool_call["id"],
                "role": "tool",
                "name": function_name,
                "content": function_response,
            }
        )  # extend conversation with function response

        # print(messages)

        # Make a follow-up API call with the updated messages, including function call responses with tool id
        stream = client.chat.completions.create(
            model="gpt4-turbo", messages=messages, stream=True
        )  # get a new response from the model where it can see the function response
        # Prints each chunk as they come after the function is called and the result is available.
        for chunk in stream:
            if len(chunk.choices) == 0:
                continue
            if chunk.choices[0].delta.content is not None:
                print(chunk.choices[0].delta.content, end="")


print(run_conversation())
