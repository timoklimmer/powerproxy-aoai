"""
Runs all Python scripts in this folder where the filename starts with "test_".

Notes: - Whenever a script raises an exception, this script will stop automatically.
       - Disable tests by renaming their filenames such that they don't start with "test_".
       - Intentionally not using pytest here because it does not show the chunks coming in from streaming responses,
         which makes testing/demoing more difficult.
"""

import os
import subprocess

for test_filename in sorted(os.listdir(os.getcwd())):
    if test_filename.startswith("test_"):
        header = f"Running test file '{test_filename}'..."
        print("-" * len(header))
        print(f"Running test file '{test_filename}'...")
        print("-" * len(header))
        with subprocess.Popen(["python", test_filename], stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as process:
            for line in iter(process.stdout.readline, b""):
                print(line.decode(), end="")
            process.stdout.close()
            process.wait()
        if process.returncode != 0:
            print(f"\n❌ Test '{test_filename}' failed. See the stack trace above for details.")  # pylint: disable=broad-exception-raised
            break
        else:
            print(f"\n✅ Test '{test_filename}' successful.")

        print("\n")
