"""Several methods and classes around configuration."""

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar, Union
from uuid import UUID
import json
import os
import yaml
import re


T = TypeVar("T", bool, int, float, UUID, str, Enum, list, dict, None)
TEST_SUBSTITUTION = re.compile(r"({(.*)})")
CACHE: Dict[str, T] = {}


class ConfigNotFound(Exception):
    pass


def get_config(
    key: str,
    validate: Type[T],
    default: Any = None,
    required: bool = False,
    sections: Optional[Union[str, List[str]]] = None,
) -> T:
    """
    Get config from environment variable or config file.
    """
    cache_key = ".".join(
        []
        + ([] if not sections else sections if isinstance(sections, list) else [sections])
        + [key]
    )

    if cache_key in CACHE:
        return CACHE[cache_key]

    # Get config from file
    res = None
    if sections:
        if isinstance(sections, list):
            res = CONFIG
            for section in sections:
                res = res.get(section, {})
        else:
            res = CONFIG.get(sections, {})
        res = res.get(key, default)
    else:
        res = CONFIG.get(key, default)

    # Check if required
    if required and not res:
        raise ConfigNotFound(f'Cannot find config "{sections}/{key}"')

    # Convert to res_type
    try:
        if validate is str:  # str
            res = str(res)
        elif validate is bool:  # bool
            res = bool(res)
        elif validate is int:  # int
            res = int(res)
        elif validate is float:  # float
            res = float(res)
        elif validate is UUID:  # UUID
            res = UUID(res)
        elif validate is list:  # list
            res = list(res)
        elif validate is dict:  # dict
            res = dict(res)
        elif issubclass(validate, Enum):  # Enum
            res = validate(res)
    except (ValueError, TypeError, AttributeError):
        raise ConfigNotFound(
            f'Cannot convert config "{sections}/{key}" ({validate}), found "{res}" ({type(res)})'
        )

    # Check res type
    if not isinstance(res, validate):
        raise ConfigNotFound(
            f'Cannot validate config "{sections}/{key}" ({validate}), found "{res}" ({type(res)})'
        )

    res = _substitute(res)
    CACHE[cache_key] = res
    return res


def _substitute(element: Union[str, List, Dict]) -> Union[str, List, Dict]:
    """
    Replace chars surrounded by double quotes, like "{xxxx}", by the related env.
    """
    if isinstance(element, str):
        for substitution in re.findall(TEST_SUBSTITUTION, element):
            env = os.environ.get(substitution[1])
            if env:
                element = element.replace(substitution[0], env)
    elif isinstance(element, list):
        for i, v in enumerate(element):
            element[i] = _substitute(v)
    elif isinstance(element, dict):
        for k, v in element.items():
            element.update({_substitute(k): _substitute(v)})
    return element


CONFIG: Dict[str, Any] = {}
CONFIG_ENV = os.environ.get("POWERPROXY_CONFIG_JSON")

if not CONFIG_ENV:
    print('No JSON config defined from "POWERPROXY_CONFIG_JSON", pass')
else:
    try:
        CONFIG = json.loads(CONFIG_ENV)
        print("JSON config is loaded from env")
    except json.JSONDecodeError as e:
        print("Failed to load JSON config from env")
        print(e)

if not CONFIG:
    CONFIG_FILE = os.environ.get("POWERPROXY_CONFIG_FILE", "config.yaml")
    CONFIG_FOLDER = Path(os.environ.get("POWERPROXY_CONFIG_PATH", ".")).absolute()
    CONFIG_PATH: Union[str, None] = None
    while CONFIG_FOLDER:
        CONFIG_PATH = f"{CONFIG_FOLDER}/{CONFIG_FILE}"
        print(f'Try to load config from "{CONFIG_PATH}"')
        try:
            with open(CONFIG_PATH, "rb") as file:
                CONFIG = yaml.safe_load(file)
            break
        except FileNotFoundError:
            if CONFIG_FOLDER.parent == CONFIG_FOLDER:
                raise ConfigNotFound("Cannot find config file")
            CONFIG_FOLDER = CONFIG_FOLDER.parent.parent
        except Exception as e:
            print(f'Cannot load config file "{CONFIG_PATH}"')
            raise e
    print(f'Config "{CONFIG_PATH}" loaded')
