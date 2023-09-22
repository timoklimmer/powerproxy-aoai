from helpers.config import get_config
from helpers.logger import enable_app_insights
from helpers.logger import build_logger


_logger = build_logger(__name__)
ENABLED = get_config(
    "enabled", sections=["monitoring", "app_insights"], validate=bool, required=True
)


def init() -> None:
    if ENABLED:
        _setup()
        enable_app_insights()
        _logger.info("App Insights enabled")


def _setup() -> None:
    """Setup OpenTelemetry for App Insights."""
    from azure.identity import DefaultAzureCredential
    from opentelemetry._logs import get_logger_provider, set_logger_provider
    from azure.monitor.opentelemetry.exporter import (
        AzureMonitorLogExporter,
        AzureMonitorTraceExporter,
    )
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk._logs import LoggerProvider

    connection_str = get_config(
        "connection_str", sections=["monitoring", "app_insights"], validate=str, required=True
    )
    credential = DefaultAzureCredential()

    # Logs
    _logger.debug("Setting up logs exporter for App Insights")
    set_logger_provider(LoggerProvider())
    log_exporter = AzureMonitorLogExporter(connection_string=connection_str, credential=credential)
    get_logger_provider().add_log_record_processor(BatchLogRecordProcessor(log_exporter))

    # Traces
    # TODO: Enable sampling
    _logger.debug("Setting up traces exporter for App Insights")
    HTTPXClientInstrumentor().instrument()
    trace.set_tracer_provider(TracerProvider())
    trace_exporter = AzureMonitorTraceExporter(
        connection_string=connection_str, credential=credential
    )
    span_processor = BatchSpanProcessor(trace_exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)
