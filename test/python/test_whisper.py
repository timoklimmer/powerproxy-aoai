"""
Script to test the proxy's support for requests using Whisper.

Tested with openai package version 1.35.10.
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
parser.add_argument("--deployment-name", type=str, default="whisper", help="Name of Azure OpenAI deployment to test")
parser.add_argument(
    "--api-version", type=str, default="2024-06-01", help="API version to use when accessing Azure OpenAI"
)
parser.add_argument("--audio-file", type=str, default="TalkForAFewSeconds16.wav", help="Audio file to transcribe")
args, unknown = parser.parse_known_args()

client = AzureOpenAI(azure_endpoint=args.powerproxy_endpoint, api_version=args.api_version, api_key=args.api_key)

with open(args.audio_file, "rb") as audio_file:
    result = client.audio.transcriptions.create(file=audio_file, model=args.deployment_name)

print(result)
