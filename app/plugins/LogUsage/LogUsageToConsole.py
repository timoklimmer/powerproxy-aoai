"""Declares a plugin to log usage infos to console."""

from plugins.LogUsage.LogUsageBase import LogUsageBase


class LogUsageToConsole(LogUsageBase):
    """Logs Azure OpenAI usage info to console."""

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
        """Append a new line with the given infos."""
        print(
            "---\n"
            f"Request start minute           : {request_start_minute}\n"
            f"Request start minute UTC       : {request_start_minute_utc}\n"
            f"Client                         : {client}\n"
            f"Is Streaming                   : {is_streaming}\n"
            f"Prompt Tokens                  : {prompt_tokens}\n"
            f"Completion Tokens              : {completion_tokens}\n"
            f"Total Tokens                   : {total_tokens}\n"
            f"OpenAI Processing Milliseconds : {openai_processing_ms} ms\n"
            f"OpenAI Region                  : {openai_region}\n"
        )
