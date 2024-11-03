from logging import Logger
from typing import Sequence

from litestar.config.app import AppConfig
from litestar.contrib.opentelemetry import OpenTelemetryConfig, OpenTelemetryPlugin
from litestar.di import Provide
from litestar.plugins import InitPluginProtocol
from opentelemetry.metrics import Meter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import Tracer

from .base import OtelSettings, prepare_utils

DI_KEY_METER_PROVIDER = "meter"
DI_KEY_TRACER_PROVIDER = "tracer"
DI_KEY_OTEL_LOGGER = "otel_logger"


def prepare_plugins(settings: OtelSettings) -> Sequence[InitPluginProtocol]:
    meter_prov, tracer_prov, logger = prepare_utils(settings)

    otel_config = OpenTelemetryConfig(
        meter_provider=meter_prov,
        tracer_provider=tracer_prov,
    )
    otel_plugin = OpenTelemetryPlugin(otel_config)

    otel_sup_plugin = OtelSuplementalPlugin(settings, meter_prov, tracer_prov, logger)

    return otel_plugin, otel_sup_plugin


class OtelSuplementalPlugin(InitPluginProtocol):
    def __init__(
        self,
        settings: OtelSettings,
        meter_provider: MeterProvider,
        tracer_provider: TracerProvider,
        logger: Logger,
    ):
        self.config = settings
        self.meter_provider = meter_provider
        self.tracer_provider = tracer_provider
        self.logger = logger

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        def meter_fn() -> Meter:
            return self.meter_provider.get_meter("otel-demo")

        def tracer_fn() -> Tracer:
            return self.tracer_provider.get_tracer("otel-demo")

        def logger_fn() -> Logger:
            return self.logger

        app_config.dependencies[DI_KEY_METER_PROVIDER] = Provide(meter_fn, sync_to_thread=False)
        app_config.dependencies[DI_KEY_TRACER_PROVIDER] = Provide(tracer_fn, sync_to_thread=False)
        app_config.dependencies[DI_KEY_OTEL_LOGGER] = Provide(logger_fn, sync_to_thread=False)

        return app_config
