import asyncio
import logging
import os
import random
from typing import Any, Awaitable, Callable

from faststream import Depends, FastStream
from faststream.asyncapi import get_app_schema
from faststream.nats import NatsBroker, NatsRouter
from opentelemetry.trace import Tracer, get_current_span

from otel_demo.utils.base import get_otel_settings
from otel_demo.utils.faststream import OtelBundle, otel_logger, prepare_bundle, tracer_fn

from .models import Work


def get_otel_bundle() -> OtelBundle:
    settings = get_otel_settings()
    return prepare_bundle(settings)


def router_factory(name: str) -> NatsRouter:
    router = NatsRouter()
    used_queue, _ = name.split(":", 1)

    @router.subscriber("work", queue=used_queue)
    async def work_handler(
        data: Work,
        tracer: Tracer = Depends(tracer_fn),
        otel_logger=Depends(otel_logger),
    ):
        await asyncio.sleep(random.random() * 0.5 + 0.1)
        otel_logger.info(data.model_dump_json())
        main_span = get_current_span()
        main_span.add_event("I got some work")

        with tracer.start_as_current_span("process") as process_span:
            main_span.set_attribute("work_id", data.work_id)
            main_span.set_attribute("cid", data.cid)
            repeat = data.repeat
            for i in range(repeat):
                await asyncio.sleep(data.delay)
                process_span.add_event(f"Processing {i+1}/{repeat}")

    return router


def app_factory(name: str) -> FastStream:
    log_level = logging.DEBUG

    used_queue, instance = name.split(":", 1)

    nats_url = os.getenv("APP_NATS_URL", "nats://127.0.0.1:4222")
    otel_bundle = prepare_bundle(
        get_otel_settings({"client_name": name, "used_queue": used_queue, "instance": instance})
    )
    broker = NatsBroker(
        nats_url,
        log_level=log_level,
        middlewares=(otel_bundle.middeware,) if otel_bundle else [],
    )
    broker.include_routers(router_factory(name))

    on_startup: list[Callable[..., Awaitable[Any]]] = []
    if otel_bundle:
        on_startup.append(otel_bundle.on_startup)

    app = FastStream(
        broker,
        on_startup=on_startup,
    )
    return app


def app_schema() -> str:
    return get_app_schema(app_factory("a:0")).to_yaml()
