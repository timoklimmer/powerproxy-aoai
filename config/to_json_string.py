"""Return a one-line JSON string of the YAML file specified."""

import argparse
import json

import yaml

parser = argparse.ArgumentParser()
parser.add_argument("--yaml-file", type=str, help="Path to the YAML file to convert")
args = parser.parse_args()

with open(args.yaml_file, "r", encoding="utf-8") as yaml_file:
    dict_from_file = yaml.safe_load(yaml_file)

print(json.dumps(dict_from_file))
