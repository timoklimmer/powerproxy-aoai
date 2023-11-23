"""Declares a plugin which limits the usage rate for clients."""

import time

from plugins.base import TokenCountingPlugin, ImmediateResponseException
from fastapi import status
from fastapi.responses import Response


class LimitUsage(TokenCountingPlugin):
    """Limits the usage rate for clients."""

    budgets = {}
    max_tokens_per_minute_in_k_cache = {}

    def on_client_identified(self, routing_slip):
        """Run when the client has been identified."""
        super().on_client_identified(routing_slip)
        client = routing_slip["client"]

        # ensure there is a budget for the current client and minute (leaving budget as is if it
        # pre-exists for the current minute)
        current_minute = f"{time.strftime('%Y-%m-%d %H:%M')}"
        if client not in self.budgets or (
            client in self.budgets and self.budgets[client]["minute"] != current_minute
        ):
            self.budgets[client] = {
                "minute": current_minute,
                "budget": self._get_max_tokens_per_minute_in_k_for_client(client),
            }

        # ensure that the client has enough budget left for the current minute and return a 429
        # response if not
        if client in self.budgets:
            budget_entry = self.budgets[client]
            current_minute = f"{time.strftime('%Y-%m-%d %H:%M')}"
            if budget_entry["minute"] == current_minute and budget_entry["budget"] <= 0:
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
        self.budgets[client]["budget"] -= self.total_tokens

    def _get_max_tokens_per_minute_in_k_for_client(self, client):
        """Return the number of maximum tokens per minute in thousands for the given client."""
        if client not in self.max_tokens_per_minute_in_k_cache:
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
            self.max_tokens_per_minute_in_k_cache[client] = (
                float(client_settings["max_tokens_per_minute_in_k"]) * 1000
            )
        return self.max_tokens_per_minute_in_k_cache[client]
