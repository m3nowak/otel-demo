import asyncio
import os
from logging import Logger

import nats
import uvicorn
from litestar import Litestar, Request, post
from lxml import etree
from opentelemetry.propagate import inject
from opentelemetry.trace import SpanKind, Tracer, get_current_span

from otel_demo.utils.base import get_otel_settings
from otel_demo.utils.litestar import prepare_plugins

from .models import Work

NATS_URL = os.getenv("APP_NATS_URL", "nats://127.0.0.1:4222")


@post("/recieve")
async def recieve(request: Request, tracer: Tracer, otel_logger: Logger) -> str:
    with tracer.start_as_current_span("parse") as span:
        body = await request.body()
        otel_logger.info(body.decode())
        data_parsed = etree.fromstring(body)
    span_base = get_current_span()

    cid_el = data_parsed.find("cid")
    assert cid_el is not None, "No cid found in the data"
    span_base.set_attribute("cid", cid_el.text or "no-cid")

    work_id_el = data_parsed.find("workid")
    assert work_id_el is not None, "No workid found in the data"
    span_base.set_attribute("work_id", work_id_el.text or "no-workid")

    with tracer.start_as_current_span("translate") as span:
        delay_el = data_parsed.find("delay")
        assert delay_el is not None, "No delay found in the data"
        await asyncio.sleep(float(delay_el.text or "0"))
        work = Work(
            work_id=work_id_el.text,  # type: ignore
            cid=cid_el.text,  # type: ignore
            repeat=int(data_parsed.find("repeat").text),  # type: ignore
            delay=float(delay_el.text),  # type: ignore
            no_val1=int(data_parsed.find("no_val1").text),  # type: ignore
            no_val2=int(data_parsed.find("no_val2").text),  # type: ignore
            str_val1=data_parsed.find("str_val1").text,  # type: ignore
            str_val2=data_parsed.find("str_val2").text,  # type: ignore
        )
        serialized = work.model_dump_json()

    with tracer.start_as_current_span("nats") as span:
        with tracer.start_as_current_span("nats-setup") as span:
            nc = await nats.connect(NATS_URL)
        headers = {}
        inject(headers)
        with tracer.start_as_current_span("nats-send", kind=SpanKind.PRODUCER) as span:
            await nc.publish("work", serialized.encode(), headers=headers)
            otel_logger.info(serialized)
        with tracer.start_as_current_span("nats-close") as span:
            await nc.close()

    return "OK!"


def main():
    settings = get_otel_settings()
    plugins = prepare_plugins(settings)
    app = Litestar([recieve], plugins=plugins, debug=True)
    uvicorn.run(app, host="0.0.0.0", port=8000)
