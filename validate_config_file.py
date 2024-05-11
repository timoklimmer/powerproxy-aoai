"""
Validates the given config file against PowerProxy's config schema.
"""

# pylint: disable=raise-missing-from

import argparse

import jsonschema
import yaml
from jsonschema.exceptions import SchemaError, ValidationError

parser = argparse.ArgumentParser()
# --config-file
parser.add_argument(
    "--config-file",
    type=str,
    required=True,
    help="Path to config file",
)
args = parser.parse_args()

with open(args.config_file, "r", encoding="utf-8") as config_file:
    config_values_dict = yaml.safe_load(config_file)

with open("app/config.schema.json", "r", encoding="utf-8") as config_schema_file:
    schema = yaml.safe_load(config_schema_file)


try:
    jsonschema.validate(instance=config_values_dict, schema=schema)
    print(f"✅ The configuration in file '{args.config_file}' was successfully validated.")
except ValidationError as exception:
    print(f"❌ The configuration in file '{args.config_file}' is invalid. Validation message: {exception.message}")

except SchemaError:
    print(f"❌ The schema in file '{args.config_file}' is invalid.")
