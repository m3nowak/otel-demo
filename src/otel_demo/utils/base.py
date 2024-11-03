import os
from dataclasses import dataclass
from logging import INFO, Formatter, Logger, getLogger
from typing import Mapping
from urllib.parse import urljoin

from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter as GRPCLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter as GRPCMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter as GRPCSpanExporter
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter as HTTPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter as HTTPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as HTTPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


@dataclass
class OtelSettings:
    endpoint: str | None = None
    use_grpc: bool = True
    svc_name: str | None = None
    svc_ns: str | None = None
    extra_attrs: Mapping[str, int | str] | None = None

    def get_endpoint(self) -> str:
        if self.endpoint is None:
            if self.use_grpc:
                return "http://127.0.0.1:4317/"
            else:
                return "http://127.0.0.1:4318/"
        else:
            return self.endpoint


def get_otel_settings(extra_attrs: Mapping[str, int | str] | None = None) -> OtelSettings:
    return OtelSettings(
        endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
        use_grpc=os.getenv("OTEL_EXPORTER_OTLP_USE_GRPC", "1") == "1",
        svc_name=os.getenv("OTEL_SERVICE_NAME"),
        svc_ns=os.getenv("OTEL_SERVICE_NAMESPACE"),
        extra_attrs=extra_attrs,
    )


def prepare_utils(settings: OtelSettings) -> tuple[MeterProvider, TracerProvider, Logger]:
    svc_name = settings.svc_name or "rg-unnamed"
    svc_ns = settings.svc_ns or "default"
    extra_attrs = settings.extra_attrs or {}

    resource = Resource(
        attributes={
            "service.name": svc_name,
            "service.namespace": svc_ns,
            **extra_attrs,
        }
    )

    endpoint = settings.get_endpoint()

    if settings.use_grpc:
        trace_endpoint = endpoint
        otlp_span_exporter = GRPCSpanExporter(endpoint=trace_endpoint, insecure=True)
    else:
        trace_endpoint = urljoin(endpoint, "/v1/traces")
        otlp_span_exporter = HTTPSpanExporter(endpoint=trace_endpoint)
    span_processor = BatchSpanProcessor(otlp_span_exporter)
    tracer_prov = TracerProvider(resource=resource)
    tracer_prov.add_span_processor(span_processor)

    if settings.use_grpc:
        metric_endpoint = endpoint  # urljoin(endpoint, "/opentelemetry.proto.collector.trace.v1.MetricService/Export")
        otlp_metric_exporter = GRPCMetricExporter(endpoint=metric_endpoint, insecure=True)
    else:
        metric_endpoint = endpoint  # urljoin(endpoint, "/v1/metrics")
        otlp_metric_exporter = HTTPMetricExporter(endpoint=metric_endpoint)
    metric_reader = PeriodicExportingMetricReader(otlp_metric_exporter, export_interval_millis=60000)
    meter_prov = MeterProvider(metric_readers=[metric_reader], resource=resource)

    if settings.use_grpc:
        log_endpoint = endpoint  # urljoin(endpoint, "/opentelemetry.proto.collector.log.v1.LogService/Export")
        otlp_log_exporter = GRPCLogExporter(endpoint=log_endpoint, insecure=True)
    else:
        log_endpoint = urljoin(endpoint, "/v1/logs")
        otlp_log_exporter = HTTPLogExporter(endpoint=log_endpoint)
    log_processor = BatchLogRecordProcessor(otlp_log_exporter)
    log_prov = LoggerProvider(resource=resource)
    log_prov.add_log_record_processor(log_processor)
    log_handler = LoggingHandler(level=INFO, logger_provider=log_prov)
    log_handler.setFormatter(Formatter("%(message)s"))
    logger = getLogger("rg-otel")

    logger.propagate = False
    logger.addHandler(log_handler)
    logger.setLevel(INFO)
    return meter_prov, tracer_prov, logger
