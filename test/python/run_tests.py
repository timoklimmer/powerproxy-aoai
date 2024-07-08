"""
Runs all Python scripts in this folder where the filename starts with "test_".

Notes: - Whenever a script raises an exception, this script will stop automatically.
       - Disable tests by renaming their filenames such that they don't start with "test_".
       - Intentionally not using pytest here because it does not show the chunks coming in from streaming responses,
         which makes testing/demoing more difficult.
"""

import argparse
import os
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument(
    "--powerproxy-endpoint", type=str, default="http://localhost", help="Path to PowerProxy/Azure OpenAI endpoint"
)
parser.add_argument(
    "--api-key", type=str, default="04ae14bc78184621d37f1ce57a52eb7", help="API key to access PowerProxy"
)
parser.add_argument(
    "--deployment-name", type=str, default="gpt-4-turbo", help="Name of Azure OpenAI deployment to test (default)"
)
parser.add_argument(
    "--deployment-name-whisper", type=str, default="whisper", help="Name of Azure OpenAI deployment to test (Whisper)"
)
parser.add_argument(
    "--api-version", type=str, default="2024-02-01", help="API version to use when accessing Azure OpenAI"
)
args = parser.parse_args()

failed = False
for test_filename in sorted(os.listdir(os.getcwd())):
    if test_filename.startswith("test_"):
        deployment = args.deployment_name_whisper if test_filename.endswith("_whisper.py") else args.deployment_name
        header = f"Running test file '{test_filename}' on deployment '{deployment}'..."
        print("-" * len(header))
        print(header)
        print("-" * len(header))
        with subprocess.Popen(
            [
                "python",
                test_filename,
                "--powerproxy-endpoint",
                args.powerproxy_endpoint,
                "--api-key",
                args.api_key,
                "--deployment-name",
                deployment,
                "--api-version",
                args.api_version,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        ) as process:
            for line in iter(process.stdout.readline, b""):
                print(line.decode(), end="")
            process.stdout.close()
            process.wait()
        if process.returncode != 0:
            failed = True
            print(f"\n❌ Test '{test_filename}' failed. See the stack trace above for details.")  # pylint: disable=broad-exception-raised
            break
        print(f"\n✅ Test '{test_filename}' successful.")

        print("")

if not failed:
    print("\n🎉 CONGRATULATIONS -- if the script has reached to here, all tests were successful.")
