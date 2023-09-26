"""Defines the foundation for PowerProxy plugins."""

from helpers.config import get_config
from typing import Dict, Any, List
import importlib
import re


def foreach_plugin(method_name, *args):
    """
    Have each plugin run the method with the given name and arguments.
    """
    for plugin in PLUGINS:
        if hasattr(plugin, method_name):
            getattr(plugin, method_name)(*args)
        else:
            raise ValueError(
                (
                    f"Plugin class '{plugin.__class__()}' does not have a method named '{method_name}'."
                )
            )


class PowerProxyPlugin:
    """A plugin for PowerProxy, doing different things at different events."""

    def __init__(self, plugin_configuration: Dict[str, Any]):
        """Constructor."""
        self.plugin_configuration = plugin_configuration

    def on_plugin_instantiated(self):
        """Run directly after the new plugin instance has been instantiated."""

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
        return getattr(
            importlib.import_module(f"plugins.{plugin_group}.{plugin_name}"), plugin_name
        )

    @staticmethod
    def get_plugin_instance(plugin_name, plugin_configuration):
        """Return an instance of the plugin with the given name."""
        plugin_class = PowerProxyPlugin.get_plugin_class(plugin_name)
        return plugin_class(plugin_configuration)


PLUGINS: List[PowerProxyPlugin] = [
    PowerProxyPlugin.get_plugin_instance(plugin["name"], plugin)
    for plugin in get_config("plugins", validate=list, required=True)
]
foreach_plugin("on_plugin_instantiated")
