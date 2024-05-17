"""
Validates the given config file against PowerProxy's config schema.
"""

import argparse
import sys

from jsonschema.exceptions import ValidationError

sys.path.append("app")

from app.helpers.config import Configuration  # pylint: disable=wrong-import-position

parser = argparse.ArgumentParser()
# --config-file
parser.add_argument(
    "--config-file",
    type=str,
    required=True,
    help="Path to config file",
)
args = parser.parse_args()

print(f"Validating config file '{args.config_file}'...")
try:
    Configuration.validate_from_file(args.config_file, "app/config.schema.json")
    print(f"✅ Validation of config file '{args.config_file}' was successful.")
except ValidationError as exception:
    print(f"{exception}")
