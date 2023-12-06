"""Several methods and classes around configuration."""

import os

import yaml
from plugins.base import PowerProxyPlugin, foreach_plugin

from .dicts import QueryDict


class Configuration:
    """Configuration class."""

    def __init__(self, values_dict):
        """Constructor."""
        self.values_dict = QueryDict(values_dict)
        self.clients = [client["name"] for client in self.get("clients")]
        self.key_client_map = {client["key"]: client["name"] for client in self.get("clients")}
        self.plugin_names = [plugin["name"] for plugin in self.get("plugins")]

        # instantiate plugins
        self.plugins = [
            PowerProxyPlugin.get_plugin_instance(
                plugin_config["name"], self, QueryDict(plugin_config)
            )
            for plugin_config in self.get("plugins")
        ]
        foreach_plugin(self.plugins, "on_plugin_instantiated")

    def __getitem__(self, key):
        """Dunder method to get config value via ["..."] syntax."""
        return self.values_dict[key]

    def get(self, path, default=None):
        """Return value under given path."""
        return self.values_dict.get(path, default)

    def get_client_settings(self, client):
        """Return the value of a client's setting."""
        return next(
            (client_config for client_config in self["clients"] if client_config["name"] == client)
        )

    def print(self):
        """Print the current configuration."""
        Configuration.print_setting("Clients identified by API Key", ", ".join(self.clients))
        Configuration.print_setting(
            "Fixed client overwrite",
            f"{self['fixed_client'] if self['fixed_client'] else '(not set)'}",
        )
        if self["aoai/endpoints"]:
            Configuration.print_setting(
                "Azure OpenAI endpoints",
                "\n                                  ".join(
                    [
                        f"{aoai_endpoint['name']} - {aoai_endpoint['url']}"
                        for aoai_endpoint in self["aoai/endpoints"]
                    ]
                ),
            )
        if self["aoai/mock_response"]:
            Configuration.print_setting("Azure OpenAI mock response", self["aoai/mock_response"])

    @staticmethod
    def print_setting(name, value, level=0):
        """Print the given setting name and value."""
        print((f"{' ' * level * 3}{name.ljust(32) if level==0 else name}: {value}"))

    @staticmethod
    def from_file(file_path):
        """Load configuration from file."""
        with open(file_path, "r", encoding="utf-8") as file:
            return Configuration(yaml.safe_load(file))

    @staticmethod
    def from_yaml_string(yaml_string):
        """Load configuration from YAML string."""
        return Configuration(yaml.safe_load(yaml_string))

    @staticmethod
    def from_env_var(env_var_name="POWERPROXY_CONFIG_STRING", skip_no_env_var_exception=False):
        """Load configuration from environment variable."""
        if env_var_name in os.environ:
            return Configuration.from_yaml_string(os.environ[env_var_name])
        if not skip_no_env_var_exception:
            raise ValueError(
                f"Cannot load configuration from environment variable '{env_var_name}' because it "
                f"does not exist."
            )
        return None

    @staticmethod
    def from_args(args):
        """Load configuration from script arguments."""
        result = None
        if args.config_file:
            result = Configuration.from_file(args.config_file)
        elif args.config_env_var and args.config_env_var in os.environ:
            result = Configuration.from_env_var(args.config_env_var)
        elif args.config_env_var and args.config_env_var not in os.environ:
            raise ValueError(
                (
                    f"The specified environment variable '{args.config_env_var}', which shall "
                    "contain the configuration for PowerProxy, does not exist."
                )
            )
        elif "POWERPROXY_CONFIG_STRING" in os.environ:
            result = Configuration.from_env_var(
                "POWERPROXY_CONFIG_STRING", skip_no_env_var_exception=True
            )
        else:
            raise ValueError(
                (
                    "No configuration provided. Ensure that you pass in a valid configuration "
                    "either by using argument '--config-file' or '-config-env-var', or provide a "
                    "valid config string in env variable named 'POWERPROXY_CONFIG_STRING' "
                    "(in YAML format)."
                )
            )
        return result
