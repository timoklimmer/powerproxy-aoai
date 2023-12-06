"""Declares a plugin to log usage infos to console."""

from plugins.LogUsage.LogUsageBase import LogUsageBase


class LogUsageToConsole(LogUsageBase):
    """Logs Azure OpenAI usage info to console."""

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
        print(
            "---\n"
            f"Request received UTC        : {request_received_utc}\n"
            f"Client                      : {client}\n"
            f"Is Streaming                : {is_streaming}\n"
            f"Prompt Tokens               : {prompt_tokens}\n"
            f"Completion Tokens           : {completion_tokens}\n"
            f"Total Tokens                : {total_tokens}\n"
            f"Azure OpenAI Roundtrip Time : {aoai_roundtrip_time_ms} ms\n"
            f"Azure OpenAI Region         : {aoai_region}\n"
            f"Azure OpenAI Endpoint Name  : {aoai_endpoint_name}\n"
        )
