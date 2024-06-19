"""Several methods and classes around configuration."""

import os

import jsonschema
import yaml
from jsonschema.exceptions import SchemaError, ValidationError
from plugins.base import PowerProxyPlugin, foreach_plugin

from .dicts import QueryDict


class Configuration:
    """Configuration class."""

    def __init__(self, values_dict):
        """Constructor."""
        Configuration.validate_from_dict(values_dict)
        self.values_dict = QueryDict(values_dict)
        self.clients = [client["name"] for client in self.get("clients")]
        self.entra_id_client = None
        for client in self.get("clients"):
            if "uses_entra_id_auth" in client and client["uses_entra_id_auth"]:
                self.entra_id_client = client
        self.key_client_map = {client["key"]: client["name"] for client in self.get("clients") if "key" in client}
        self.plugin_names = [plugin["name"] for plugin in self.get("plugins") or []]
        self.plugins = [
            PowerProxyPlugin.get_plugin_instance(plugin_config["name"], self, QueryDict(plugin_config))
            for plugin_config in self.get("plugins", [])
        ]
        foreach_plugin(self.plugins, "on_plugin_instantiated")

    @staticmethod
    def validate_from_file(config_file, config_schema_file="config.schema.json"):
        """Validates the config in a configuration file."""
        with open(config_file, "r", encoding="utf-8") as file:
            config_values_dict = yaml.safe_load(file)
        Configuration.validate_from_dict(config_values_dict, config_schema_file)

    @staticmethod
    def validate_from_dict(values_dict, config_schema_file="config.schema.json"):
        """Validate the given configuration."""
        # validate against config schema file
        with open(config_schema_file, "r", encoding="utf-8") as config_schema_file:
            schema = yaml.safe_load(config_schema_file)
        try:
            jsonschema.validate(instance=values_dict, schema=schema)
        except ValidationError as exception:
            raise ValidationError(f"❌ The given configuration is invalid.\n{exception}") from exception
        except SchemaError as exception:
            raise SchemaError(f"❌ The given schema for the config file is invalid.\n{exception}") from exception
        # validate non_streaming_fraction (jsonschema cannot validate that, so we need to validate on our own here)
        if "endpoints" in values_dict["aoai"]:
            endpoints = values_dict["aoai"]["endpoints"]
            last_endpoint = endpoints[-1]
            if "non_streaming_fraction" in last_endpoint and float(last_endpoint["non_streaming_fraction"]) != 1:
                raise ValidationError(
                    (
                        "❌ If a non_streaming_fraction is specified for the last endpoint in the configuration, its "
                        "non_streaming_fraction value needs to be set to 1 so there is at least one endpoint to serve "
                        f"non-streaming requests. Ensure that endpoint '{last_endpoint['name']}' has either a "
                        "non_streaming_fraction value of 1 or no non_streaming_fraction value at all."
                    )
                )
            for endpoint in endpoints:
                if "virtual_deployments" in endpoint:
                    virtual_deployments = endpoint["virtual_deployments"]
                    for virtual_deployment in virtual_deployments:
                        standins = virtual_deployment["standins"]
                        last_standin = standins[-1]
                        if "non_streaming_fraction" in last_standin and last_standin["non_streaming_fraction"] != 1:
                            raise ValidationError(
                                (
                                    "❌ If a non_streaming_fraction is specified for the last standin in the "
                                    "configuration of a virtual deployment, its non_streaming_fraction value needs to "
                                    "be set to 1 so there is at least one standin to serve non-streaming requests. "
                                    f"Ensure that standin '{last_standin['name']}' at endpoint '{endpoint['name']}', "
                                    f"virtual deployment '{virtual_deployment['name']}' has either a "
                                    f"non_streaming_fraction value of 1 or no non_streaming_fraction value at all."
                                )
                            )
        # validate plugin and client configurations
        for plugin_config in values_dict.get("plugins", []):
            plugin_class = PowerProxyPlugin.get_plugin_class(plugin_config["name"])
            plugin_config_jsonschema = getattr(plugin_class, "plugin_config_jsonschema")
            client_config_jsonschema = getattr(plugin_class, "client_config_jsonschema")
            # plugins
            if plugin_config_jsonschema:
                try:
                    jsonschema.validate(instance=plugin_config, schema=plugin_config_jsonschema)
                except ValidationError as exception:
                    raise ValidationError(
                        f"❌ The configuration for plugin '{plugin_class.__name__}' is invalid.\n{exception}"
                    ) from exception
                except SchemaError as exception:
                    raise SchemaError(
                        f"❌ The schema for plugin '{plugin_class.__name__}' is invalid.\n{exception}"
                    ) from exception
            # clients
            if client_config_jsonschema:
                for client in values_dict.get("clients"):
                    try:
                        jsonschema.validate(instance=client, schema=client_config_jsonschema)
                    except ValidationError as exception:
                        raise ValidationError(
                            f"❌ The configuration for client '{client['name']}' is invalid.\n{exception}"
                        ) from exception
                    except SchemaError as exception:
                        raise SchemaError(
                            f"❌ The client config schema in plugin '{plugin_class.__name__}' is invalid.\n{exception}"
                        ) from exception

    def __getitem__(self, key):
        """Dunder method to get config value via ["..."] syntax."""
        return self.values_dict[key]

    def get(self, path, default=None):
        """Return value under given path."""
        return self.values_dict.get(path, default)

    def get_client_settings(self, client):
        """Return the value of a client's setting."""
        return next((client_config for client_config in self["clients"] if client_config["name"] == client))

    def print(self):
        """Print the current configuration."""
        Configuration.print_setting("Clients", ", ".join(self.clients))
        Configuration.print_setting(
            "Entra ID Client",
            f"{self.entra_id_client['name'] if self.entra_id_client else '(not set)'}",
        )
        if self["aoai/endpoints"]:
            Configuration.print_setting_header("Azure OpenAI")
            for aoai_endpoint in self["aoai/endpoints"]:
                Configuration.print_line(f"{aoai_endpoint['name']} - {aoai_endpoint['url']}", level=1)
                for item in aoai_endpoint.keys() - ["name", "url", "key", "connections", "virtual_deployments"]:
                    Configuration.print_line(f"{item}: {aoai_endpoint[item]}", level=2)
                if "connections" in aoai_endpoint:
                    Configuration.print_setting("Connections", f"{aoai_endpoint['connections']}", level=2)
                if "virtual_deployments" in aoai_endpoint:
                    for deployment in aoai_endpoint["virtual_deployments"]:
                        Configuration.print_line(f"- {deployment['name']}", level=2)
                        for standin in deployment["standins"]:
                            standin_config_string = ", ".join(
                                [f"{item}: {standin[item]}" for item in standin if item != "name"]
                            )
                            standin_config_string = f" ({standin_config_string})" if standin_config_string else ""
                            Configuration.print_line(
                                f"    └ {standin['name']}{standin_config_string}",
                                level=2,
                            )

            Configuration.print_line("")
        if self["aoai/mock_response"]:
            Configuration.print_setting("Azure OpenAI mock response", self["aoai/mock_response"])

    @staticmethod
    def print_setting_header(name):
        """Print the given setting header."""
        print(name)

    @staticmethod
    def print_setting(name, value, level=0):
        """Print the given setting name and value."""
        print((f"{' ' * level * 3}{name.ljust(32) if level==0 else name}: {value}"))

    @staticmethod
    def print_line(line, level=0):
        """Print the given setting name and value."""
        print((f"{' ' * level * 3}{line}"))

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
                f"Cannot load configuration from environment variable '{env_var_name}' because it " f"does not exist."
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
            result = Configuration.from_env_var("POWERPROXY_CONFIG_STRING", skip_no_env_var_exception=True)
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
