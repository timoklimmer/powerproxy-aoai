"""Defines the foundation for PowerProxy plugins."""

import importlib
import re

import jsonschema
from helpers.tokens import estimate_prompt_tokens_from_request_body_dict
from jsonschema.exceptions import SchemaError, ValidationError


def foreach_plugin(plugins, method_name, *args):
    """Have each plugin run the method with the given name and arguments."""
    for plugin in plugins:
        if hasattr(plugin, method_name):
            getattr(plugin, method_name)(*args)
        else:
            raise ValueError(
                (f"Plugin class '{plugin.__class__.__name__}' does not have a method named " f"'{method_name}'.")
            )


class PowerProxyPlugin:
    """A plugin for PowerProxy, doing different things at different events."""

    plugin_config_jsonschema = None
    client_config_jsonschema = None

    def __init__(self, app_configuration, plugin_configuration):
        """Constructor."""
        self.app_configuration = app_configuration
        self.plugin_configuration = plugin_configuration
        self.validate_plugin_configuration()
        self.validate_client_configurations()

    def validate_plugin_configuration(self):
        """Validate if the configuration given to the plugin is valid."""
        if self.plugin_configuration and self.plugin_config_jsonschema:
            try:
                jsonschema.validate(instance=self.plugin_configuration, schema=self.plugin_config_jsonschema)
            except ValidationError as exception:
                raise ValueError(
                    f"❌ The configuration for plugin '{self.__class__.__name__}' is invalid.\n{exception}"
                ) from exception
            except SchemaError as exception:
                raise ValueError(
                    f"❌ The schema for plugin '{self.__class__.__name__}' is invalid.\n{exception}"
                ) from exception

    def validate_client_configurations(self):
        """Validate each configured client and check if it has all info required by the plugin."""
        if self.client_config_jsonschema:
            for client in self.app_configuration["clients"]:
                try:
                    jsonschema.validate(instance=client, schema=self.client_config_jsonschema)
                except ValidationError as exception:
                    raise ValueError(
                        f"❌ The configuration for client '{client['name']}' is invalid.\n{exception}"
                    ) from exception
                except SchemaError as exception:
                    raise ValueError(
                        f"❌ The client config schema in plugin '{self.__class__.__name__}' is invalid.\n{exception}"
                    ) from exception

    def on_plugin_instantiated(self):
        """Run directly after the new plugin instance has been instantiated."""

    def on_print_configuration(self):
        """Print plugin-specific configuration."""
        print(f"Plugin: {self.__class__.__name__}")

    def on_new_request_received(self, routing_slip):
        """Run when a new request has been received."""

    def on_client_identified(self, routing_slip):
        """Run when the client has been identified."""

    def on_headers_from_target_received(self, routing_slip):
        """Run when the headers from the target have been received."""

    def on_body_dict_from_target_available(self, routing_slip):
        """Run when the body returned from the target could be converted to a dict."""

    def on_data_event_from_target_received(self, routing_slip):
        """Run when a data event has been received from the target (only on streaming)."""

    def on_end_of_target_response_stream_reached(self, routing_slip):
        """Run when the end of the target's response stream has been reached (only on streaming)."""

    @staticmethod
    def get_plugin_class(plugin_name):
        """Return the class for the given plugin name."""
        plugin_group = re.sub("To.+$", "", plugin_name)
        return getattr(importlib.import_module(f"plugins.{plugin_group}.{plugin_name}"), plugin_name)

    @staticmethod
    def get_plugin_instance(plugin_name, app_configuration, plugin_configuration):
        """Return an instance of the plugin with the given name."""
        plugin_class = PowerProxyPlugin.get_plugin_class(plugin_name)
        return plugin_class(app_configuration, plugin_configuration)


class TokenCountingPlugin(PowerProxyPlugin):
    """A plugin which counts tokens."""

    prompt_tokens = None
    streaming_prompt_tokens = None
    completion_tokens = None
    streaming_completion_tokens = None
    total_tokens = None

    def on_new_request_received(self, routing_slip):
        """Run when a new request is received."""
        super().on_new_request_received(routing_slip)

        self.prompt_tokens = None
        self.completion_tokens = None
        self.streaming_prompt_tokens = None
        self.streaming_completion_tokens = None
        self.total_tokens = None

    def on_body_dict_from_target_available(self, routing_slip):
        """Run when the body was received from AOAI (only for one-time, non-streaming requests)."""
        super().on_body_dict_from_target_available(routing_slip)

        usage = routing_slip["body_dict_from_target"]["usage"]
        self.completion_tokens = usage.get("completion_tokens", 0)
        self.prompt_tokens = usage["prompt_tokens"]
        self.total_tokens = usage["total_tokens"]

        self.on_token_counts_for_request_available(routing_slip)

    def on_data_event_from_target_received(self, routing_slip):
        """Run when a data event has been received by AOAI (needs streaming requested)."""
        super().on_data_event_from_target_received(routing_slip)

        self.streaming_completion_tokens = (
            self.streaming_completion_tokens + 1 if self.streaming_completion_tokens else 1
        )

    def on_end_of_target_response_stream_reached(self, routing_slip):
        """Process the end of a stream (needs streaming requested)."""
        super().on_end_of_target_response_stream_reached(routing_slip)

        self.prompt_tokens = estimate_prompt_tokens_from_request_body_dict(routing_slip["incoming_request_body_dict"])
        self.completion_tokens = self.streaming_completion_tokens
        self.total_tokens = (
            self.prompt_tokens + self.completion_tokens
            if self.prompt_tokens is not None and self.completion_tokens is not None
            else None
        )
        self.on_token_counts_for_request_available(routing_slip)

    def on_token_counts_for_request_available(self, routing_slip):
        """Is invoked when token counts are available for the request."""


class ImmediateResponseException(Exception):
    """Exception thrown when a plugin needs a certain response returned immediately."""

    def __init__(self, response):
        """Constructor."""
        self.response = response
