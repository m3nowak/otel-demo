import asyncio
import random
import uuid

from httpx import AsyncClient
from lxml.builder import E
from lxml.etree import tostring
from opentelemetry import trace
from opentelemetry.propagate import inject

from otel_demo.utils.base import get_otel_settings, prepare_utils


async def main(target: str | None = None):
    settings = get_otel_settings()
    _, tracer_provider, logger = prepare_utils(settings)

    tracer = tracer_provider.get_tracer(__name__)

    if target is None:
        target = "http://localhost:8000/recieve"
    while True:
        with tracer.start_as_current_span("producer") as span:
            span.set_attribute("target", target)
            work_id = f"work-{random.randint(1, 9999)}"
            cid = uuid.uuid4().hex

            work = E.work(
                E.workid(work_id),
                E.cid(cid),
                E.repeat(f"{random.randint(1, 3)}"),
                E.delay(f"{random.random()*2+0.5:.2f}"),
                E.no_val1(f"{random.randint(1, 100)}"),
                E.no_val2(f"{random.randint(1, 100)}"),
                E.str_val1(f"str-{random.randint(1, 100)}"),
                E.str_val2(f"str-{random.randint(1, 100)}"),
            )
            span.set_attribute("work_id", work_id)
            span.set_attribute("cid", cid)

            headers = {}
            inject(headers)
            with tracer.start_as_current_span("send", kind=trace.SpanKind.PRODUCER) as send_span:
                async with AsyncClient() as client:
                    try:
                        resp = await client.post(target, content=tostring(work, encoding="unicode"), headers=headers)
                        send_span.set_attribute("status", resp.status_code)
                        send_span.add_event("I got a response")
                        logger.info(resp.text)
                    except Exception as e:
                        send_span.record_exception(e)
                        send_span.add_event("I got an error")
            sleep_time = random.randint(2, 10)
            span.add_event(f"Will sleep for {sleep_time}", {"sleep_time": sleep_time})
        await asyncio.sleep(sleep_time)
