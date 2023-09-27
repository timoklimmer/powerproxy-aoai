"""Declares the base class for a plugin that logs usage information."""

# pylint: disable=invalid-name,import-error,no-name-in-module,too-many-arguments,too-many-instance-attributes

import datetime
import time
from abc import abstractmethod
from datetime import timezone

from plugins.base import TokenCountingPlugin


class LogUsageBase(TokenCountingPlugin):
    """Base class for a plugin that logs usage."""

    openai_region = None
    openai_processing_ms = None
    openai_region = None
    request_start_minute = None
    request_start_minute_utc = None

    def on_new_request_received(self, routing_slip):
        """Run when a new request is received."""
        super().on_new_request_received(routing_slip)

        self.openai_region = None
        self.openai_processing_ms = None
        self.openai_region = None
        self.request_start_minute = f"{time.strftime('%Y-%m-%d %H:%M')}"
        self.request_start_minute_utc = f"{datetime.datetime.now(timezone.utc):%Y-%m-%d %H:%M}"

    def on_headers_from_target_received(self, routing_slip):
        """Run when headers from target have been received."""
        super().on_headers_from_target_received(routing_slip)

        headers_from_target = routing_slip["headers_from_target"]
        for header, value in headers_from_target.items():
            if header == "openai-processing-ms":
                self.openai_processing_ms = float(value)
            if header == "x-ms-region":
                self.openai_region = value

    def on_body_dict_from_target_available(self, routing_slip):
        """Run when the body was received from AOAI (only for one-time, non-streaming requests)."""
        super().on_body_dict_from_target_available(routing_slip)

        self._append_line(
            request_start_minute=self.request_start_minute,
            request_start_minute_utc=self.request_start_minute_utc,
            client=routing_slip["client"],
            is_streaming=False,
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            total_tokens=self.total_tokens,
            openai_processing_ms=self.openai_processing_ms,
            openai_region=self.openai_region,
        )

    def on_end_of_target_response_stream_reached(self, routing_slip):
        """Process the end of a stream (needs streaming requested)."""
        super().on_end_of_target_response_stream_reached(routing_slip)

        self._append_line(
            request_start_minute=self.request_start_minute,
            request_start_minute_utc=self.request_start_minute_utc,
            client=routing_slip["client"],
            is_streaming=True,
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            total_tokens=self.total_tokens,
            openai_processing_ms=self.openai_processing_ms,
            openai_region=self.openai_region,
        )

    @abstractmethod
    def _append_line(
        self,
        request_start_minute,
        request_start_minute_utc,
        client,
        is_streaming,
        prompt_tokens,
        completion_tokens,
        total_tokens,
        openai_processing_ms,
        openai_region,
    ):
        pass
