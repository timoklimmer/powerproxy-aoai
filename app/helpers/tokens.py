"""Several methods around tokens."""

# notes:
# - for non-streaming responses, usage info is provided in Azure OpenAI's response. Try to use these
#   infos wherever possible.
# - for streaming responses, (Azure) OpenAI do not provide accurate usage infos, unfortunately.
#   hence, tokens need to be estimated. since there is no proper documentation, these estimations
#   might not be accurate but still more useful than no estimations. as of now, functions are not
#   taken into account. for exact numbers, disable the streaming mode.
# - code here is based on infos provided at
#   https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb
# - code will need update as new models come out and more documentation or usage infos are available

import tiktoken


def estimate_prompt_tokens_from_request_body_dict(request_body_dict):
    """Return the estimated number of tokes in the given request body string."""
    if request_body_dict is None or "messages" not in request_body_dict:
        return 0
    return estimate_tokens_from_messages(request_body_dict["messages"])


def estimate_tokens_from_string(string, encoding_name="cl100k_base"):
    """Return the estimated number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens


def estimate_tokens_from_messages(messages, model="gpt-3.5-turbo-0613"):
    """Return the estimated number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    if model in {
        "gpt-3.5-turbo",
        "gpt-3.5-turbo-0613",
        "gpt-3.5-turbo-16k-0613",
        "gpt-4-0314",
        "gpt-4-32k-0314",
        "gpt-4",
        "gpt-4-0613",
        "gpt-4-32k-0613",
    }:
        tokens_per_message = 3
        tokens_per_name = 1
    elif model == "gpt-3.5-turbo-0301":
        tokens_per_message = 4  # every message follows <|start|>{role/name}\n{content}<|end|>\n
        tokens_per_name = -1  # if there's a name, the role is omitted
    else:
        raise NotImplementedError(
            f"Method is not implemented for model {model}. See "
            "https://github.com/openai/openai-python/blob/main/chatml.md for information on how "
            "messages are converted to tokens."
        )
    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name
    num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
    return num_tokens
