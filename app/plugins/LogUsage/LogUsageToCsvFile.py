"""Declares a plugin to log usage infos to a CSV file."""

import os
import time

from plugins.LogUsage.LogUsageBase import LogUsageBase


class LogUsageToCsvFile(LogUsageBase):
    """Logs Azure OpenAI usage info to CSV file."""

    log_dir = None
    log_file_name = None
    log_file_path = None

    columns = [
        "request_received_utc",
        "client",
        "is_streaming",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "aoai_roundtrip_time_ms",
        "aoai_region",
        "aoai_endpoint_name",
    ]

    def on_plugin_instantiated(self):
        """Run directly after the new plugin instance has been instantiated."""
        super().on_plugin_instantiated()

        # set log file etc.
        self.log_dir = "../logs"
        self.log_file_name = f"{time.strftime('%Y%m%d-%H%M%S')}.logs.csv"
        self.log_file_path = os.path.join(self.log_dir, self.log_file_name)

        # ensure we have a logs directory
        if not os.path.exists(self.log_dir):
            os.mkdir(self.log_dir)

        # create a new file containing the header for the CSV file
        with open(self.log_file_path, "w", encoding="utf-8") as log_file:
            log_file.write(",".join(self.columns))

    def _append_line(
        self,
        request_received_utc,
        client,
        is_streaming,
        prompt_tokens,
        completion_tokens,
        total_tokens,
        aoai_roundtrip_time_ms,
        aoai_region,
        aoai_endpoint_name,
    ):
        """Append a new line with the given infos."""
        with open(self.log_file_path, "a", encoding="utf-8") as log_file:
            log_file.write(
                "\n"
                f"{request_received_utc},"
                f"{client},"
                f"{1 if is_streaming else 0},"
                f"{prompt_tokens},"
                f"{completion_tokens},"
                f"{total_tokens},"
                f"{aoai_roundtrip_time_ms},"
                f"{aoai_region},"
                f"{aoai_endpoint_name}"
            )
