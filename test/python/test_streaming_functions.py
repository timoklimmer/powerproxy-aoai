"""Script to test the proxy's ability to support response streaming when functions are used."""

from openai import AzureOpenAI
import json


client = AzureOpenAI(
    azure_endpoint="http://localhost",
    api_version="2023-12-01-preview",
    api_key="04ae14bc78184621d37f1ce57a52eb7",
)

def search_hotels(location, max_price, features):
    if location == "San Diego":
        return json.dumps([{"name": "Hotel 1", "price": 200, "features": ["beachfront", "free breakfast"]}, {"name": "Hotel 2", "price": 250, "features": ["beachfront", "free breakfast"]}])
    else:
        return json.dumps({"location": location, "temperature": "unknown"})


def run_conversation():
    messages = [{"role": "user", "content": "Find beachfront hotels in San Diego for less than $300 a month with free breakfast."}]
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
            }
        }
    ]
    response = client.chat.completions.create(
        model="35turbo",
        messages=messages,
        tools=tools,
        temperature=0,
        tool_choice="auto",
        stream=True,
    )

    response_message = ''

    for chunk in response:
        response_message +=str(chunk)+ "\n"
        return response_message

    tool_calls = response_message.tool_calls

    if tool_calls:
        # Step 3: call the function
        # Note: the JSON response may not always be valid; be sure to handle errors
        available_functions = {
            "search_hotels": search_hotels,
        }  # only one function in this example, but you can have multiple
        messages.append(response_message)  # extend conversation with assistant's reply
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_to_call = available_functions[function_name]
            function_args = json.loads(tool_call.function.arguments)
            function_response = function_to_call(
                location=function_args.get("location"),
                max_price=function_args.get("max_price"),
                features=function_args.get("features")
            )
            messages.append(
                {
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": function_response,
                }
            )  # extend conversation with function response
        second_response = client.chat.completions.create(
            model="35turbo",
            messages=messages,
        )  # get a new response from the model where it can see the function response
        return second_response

print(run_conversation())
