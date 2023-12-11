"""Declares a plugin which limits the usage rate for clients."""

import time

import redis
from fastapi import status
from fastapi.responses import Response
from helpers.config import Configuration
from plugins.base import ImmediateResponseException, TokenCountingPlugin


class LimitUsage(TokenCountingPlugin):
    """Limits the usage rate for clients."""

    configured_max_tpms = {}
    local_cache = {}
    redis_cache = None
    redis_host = None
    redis_password = None

    def on_plugin_instantiated(self):
        """Run directly after the new plugin instance has been instantiated."""
        if "redis" in self.plugin_configuration:
            self.redis_host = self.plugin_configuration["redis/redis_host"]
            self.redis_password = self.plugin_configuration["redis/redis_password"]
            self.redis_cache = redis.StrictRedis(
                host=self.redis_host,
                port=6380,
                db=0,
                password=self.redis_password,
                ssl=True,
            )

    def on_print_configuration(self):
        """Print plugin-specific configuration."""
        super().on_print_configuration()
        Configuration.print_setting("Redis Host", self.redis_host or "(none)", 1)

    def on_client_identified(self, routing_slip):
        """Run when the client has been identified."""
        super().on_client_identified(routing_slip)
        client = routing_slip["client"]

        # ensure there is a budget for the current client and minute, leaving budget as is if it
        # pre-exists for the current minute
        current_minute = int(time.time() / 60)
        current_minute_from_cache = int(self._get_cache_setting(f"LimitUsage-{client}-minute") or 0)
        if not current_minute_from_cache or current_minute_from_cache != current_minute:
            self._set_cache_setting(f"LimitUsage-{client}-minute", current_minute)
            self._set_cache_setting(
                f"LimitUsage-{client}-budget",
                self._get_max_tokens_per_minute_in_k_for_client(client),
            )

        # ensure that the client has enough budget left for the current minute and return a 429
        # response if not
        current_minute_from_cache = int(self._get_cache_setting(f"LimitUsage-{client}-minute"))
        current_budget_from_cache = int(self._get_cache_setting(f"LimitUsage-{client}-budget"))
        if current_minute_from_cache == current_minute and current_budget_from_cache <= 0:
            raise ImmediateResponseException(
                Response(
                    content=f"Too many requests for client '{client}'. Try again later.",
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                )
            )

    def on_token_counts_for_request_available(self, routing_slip):
        """Is invoked when token counts are available for the request."""
        super().on_token_counts_for_request_available(routing_slip)

        # decrement the client's budget by the total tokens
        client = routing_slip["client"]
        old_budget = int(self._get_cache_setting(f"LimitUsage-{client}-budget"))
        new_budget = old_budget - self.total_tokens
        self._set_cache_setting(f"LimitUsage-{client}-budget", new_budget)

    def _get_cache_setting(self, key, default=None):
        """Return the setting with the given key from the cache."""
        if self.redis_cache:
            return self.redis_cache.get(key)
        return self.local_cache.get(key, default)

    def _set_cache_setting(self, key, value):
        """Return the setting with the given key from the cache."""
        if self.redis_cache:
            self.redis_cache.set(key, value)
        else:
            self.local_cache[key] = value

    def _get_max_tokens_per_minute_in_k_for_client(self, client):
        """Return the number of maximum tokens per minute in thousands for the given client."""
        if client not in self.configured_max_tpms:
            client_settings = self.app_configuration.get_client_settings(client)
            if "max_tokens_per_minute_in_k" not in client_settings:
                raise ImmediateResponseException(
                    Response(
                        content=(
                            f"Configuration for client '{client}' misses a "
                            "'max_tokens_per_minute_in_k' setting. This needs to be set when the "
                            "LimitUsage plugin is enabled."
                        ),
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )
                )
            self.configured_max_tpms[client] = int(
                float(client_settings["max_tokens_per_minute_in_k"]) * 1000
            )
        return self.configured_max_tpms[client]
