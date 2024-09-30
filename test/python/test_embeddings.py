"""
Script to test the proxy's ability to support embeddings.
"""

import argparse

from openai import AzureOpenAI

parser = argparse.ArgumentParser()
parser.add_argument(
    "--powerproxy-endpoint", type=str, default="http://localhost", help="Path to PowerProxy/Azure OpenAI endpoint"
)
parser.add_argument(
    "--api-key", type=str, default="04ae14bc78184621d37f1ce57a52eb7", help="API key to access PowerProxy"
)
parser.add_argument(
    "--deployment-name",
    type=str,
    default="text-embedding-ada-002",
    help="Name of Azure OpenAI deployment to test (Embedding)",
)
parser.add_argument(
    "--api-version", type=str, default="2024-06-01", help="API version to use when accessing Azure OpenAI"
)
args, unknown = parser.parse_known_args()

client = AzureOpenAI(
    azure_endpoint=args.powerproxy_endpoint,
    api_version=args.api_version,
    api_key=args.api_key,
)

text = "Hello world! How are you today?"
embedding = client.embeddings.create(input=[text], model=args.deployment_name).data[0].embedding
print(f"Embedding for '{text}' is '{embedding}'")
