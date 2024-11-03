from dataclasses import dataclass
from logging import Logger, getLogger
from typing import Awaitable, Callable

from faststream import ContextRepo, Depends
from faststream.nats.opentelemetry import NatsTelemetryMiddleware
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import Tracer

from .base import OtelSettings, prepare_utils


@dataclass
class OtelBundle:
    on_startup: Callable[..., Awaitable[None]]
    middeware: NatsTelemetryMiddleware


def on_startup_factory(tracer_provider: TracerProvider, meter_provider: MeterProvider, otel_logger: Logger):
    async def on_startup(context: ContextRepo):
        context.set_global("tracer_provider", tracer_provider)
        context.set_global("meter_provider", meter_provider)
        context.set_global("otel_logger", otel_logger)

    return on_startup


def prepare_bundle(settings: OtelSettings):
    meter_prov, tracer_prov, logger = prepare_utils(settings)
    return direct_prepare_bundle(meter_prov, tracer_prov, logger)


def direct_prepare_bundle(meter_prov: MeterProvider, tracer_prov: TracerProvider, logger: Logger):
    return OtelBundle(
        on_startup=on_startup_factory(tracer_provider=tracer_prov, meter_provider=meter_prov, otel_logger=logger),
        middeware=NatsTelemetryMiddleware(tracer_provider=tracer_prov, meter_provider=meter_prov),
    )


def tracer_provider(context: ContextRepo) -> TracerProvider:
    return context.get("tracer_provider")


def tracer_fn(tracer_provider: TracerProvider = Depends(tracer_provider)) -> Tracer:
    return tracer_provider.get_tracer("rg-app.faststream.otel")


def meter_provider(context: ContextRepo) -> MeterProvider:
    return context.get("meter_provider")


def meter_fn(meter_provider: MeterProvider = Depends(meter_provider)):
    return meter_provider.get_meter("rg-app.faststream.otel")


def otel_logger(context: ContextRepo) -> Logger:
    return getLogger("rg-otel")
