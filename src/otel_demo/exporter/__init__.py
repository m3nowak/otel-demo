# __init__.py
# from concurrent import futures
import asyncio
import hashlib
import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import grpc
from google.protobuf.internal.containers import RepeatedCompositeFieldContainer
from grpc_reflection.v1alpha import reflection
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import DESCRIPTOR as LOGS_DESCRIPTOR
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import ExportLogsServiceRequest, ExportLogsServiceResponse
from opentelemetry.proto.collector.logs.v1.logs_service_pb2_grpc import LogsServiceServicer as OGLogsServiceServicer
from opentelemetry.proto.collector.logs.v1.logs_service_pb2_grpc import add_LogsServiceServicer_to_server
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import DESCRIPTOR as TRACE_DESCRIPTOR

# from opentelemetry.proto.collector.trace.v1.trace_service_pb2_grpc import TraceServiceStub
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
    ExportTraceServiceResponse,
)
from opentelemetry.proto.collector.trace.v1.trace_service_pb2_grpc import TraceServiceServicer as OGTraceServiceServicer
from opentelemetry.proto.collector.trace.v1.trace_service_pb2_grpc import add_TraceServiceServicer_to_server
from opentelemetry.proto.common.v1.common_pb2 import AnyValue, KeyValue
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .tables import Base, Event, Log, Span

logging.basicConfig(level=logging.DEBUG)


def extract_anyvalue(value: AnyValue):
    stupid_wrapper_helper = value.WhichOneof("value")
    if stupid_wrapper_helper:
        return getattr(value, stupid_wrapper_helper)
    else:
        return None


def normalize_attributes(attributes: RepeatedCompositeFieldContainer[KeyValue]):
    dct_attr = {}
    for a in attributes:
        dct_attr[a.key] = extract_anyvalue(a.value)
    return dct_attr


def bytes_to_hex_str(b: bytes) -> str:
    return b.hex()


class LogService(OGLogsServiceServicer):
    def __init__(self, sessionmaker: async_sessionmaker) -> None:
        super().__init__()
        self.sessionmaker = sessionmaker

    async def Export(self, request: ExportLogsServiceRequest, ctx: grpc.ServicerContext) -> ExportLogsServiceResponse:
        log_objs = []
        for res_log in request.resource_logs:
            resource_attr = normalize_attributes(res_log.resource.attributes)
            for scp_log in res_log.scope_logs:
                scp_attr = normalize_attributes(scp_log.scope.attributes)
                for log_record in scp_log.log_records:
                    log_attrs = normalize_attributes(log_record.attributes)
                    trace_id = bytes_to_hex_str(log_record.trace_id) if log_record.trace_id else None
                    span_id = bytes_to_hex_str(log_record.span_id) if log_record.span_id else None
                    if trace_id and span_id:
                        identifier = f"{trace_id}-{span_id}-{log_record.time_unix_nano}"
                        identifier_hash = hashlib.sha1(identifier.encode()).hexdigest()
                        attributes = {**resource_attr, **scp_attr, **log_attrs, "exp_identifier": identifier_hash}
                        log_obj = Log(
                            trace_id=trace_id,
                            span_id=span_id,
                            log_id=uuid.uuid4(),
                            severity=log_record.severity_text,
                            time=datetime.fromtimestamp(log_record.time_unix_nano / 1e9, tz=UTC),
                            attributes=attributes,
                            body=extract_anyvalue(log_record.body),
                        )
                        log_objs.append(log_obj)
                        # print(f"resource: {res_log.resource}")
                        # print(f"scope: {scp_log.scope}")
                        # print(f"record: {log_record}")
                        # print(f"attributes: {normalize_attributes(log_record.attributes)}")
                        # print(f"body: {extract_anyvalue(log_record.body)}")
                        # print(f"severity: {log_record.severity_number}")
                        # print(f"severity_txt: {log_record.severity_text}")
                        # print(f"timestamp: {datetime.fromtimestamp(log_record.time_unix_nano / 1e9, tz=UTC)}")
                        # print(f"span_id: {bytes_to_hex_str(log_record.span_id) if log_record.span_id else None}")
                        # print(f"trace_id: {bytes_to_hex_str(log_record.trace_id) if log_record.trace_id else None}")
                        # print(f"identifier: {identifier_hash}")
        async with self.sessionmaker() as session:
            session: AsyncSession
            session.add_all(log_objs)
            await session.commit()
        print(f"logs: {len(log_objs)}")
        return ExportLogsServiceResponse()


class TraceService(OGTraceServiceServicer):
    def __init__(self, sessionmaker: async_sessionmaker) -> None:
        super().__init__()
        self.sessionmaker = sessionmaker

    async def Export(self, request: ExportTraceServiceRequest, ctx: grpc.ServicerContext) -> ExportTraceServiceResponse:
        span_objs = []
        event_objs = []
        for res_span in request.resource_spans:
            resource_attr = normalize_attributes(res_span.resource.attributes)
            for scp_span in res_span.scope_spans:
                scp_attr = normalize_attributes(scp_span.scope.attributes)
                for span in scp_span.spans:
                    # print(f"span name: {span.name}")
                    # print(f"start time: {span.start_time_unix_nano}")
                    # print(f"end time: {span.end_time_unix_nano}")
                    # print(f"trace id: {span.trace_id}")
                    # print(f"span id: {span.span_id}")
                    # print(f"parent span id: {span.parent_span_id}")
                    # print(f"kind: {span.kind}")
                    # print(f"status: {span.status}")
                    # print(f"attributes: {span.attributes}")
                    # print(f"events: {span.events}")
                    # print(f"links: {span.links}")
                    # print(f"dropped attributes count: {span.dropped_attributes_count}")
                    # print(f"dropped events count: {span.dropped_events_count}")
                    # print(f"dropped links count: {span.dropped_links_count}")
                    # print(f"status: {span.status}")
                    # print(f"start time: {span.start_time_unix_nano}")
                    # print(f"end time: {span.end_time_unix_nano}")
                    # print(f"trace state: {span.trace_state}")
                    span_attrs = normalize_attributes(span.attributes)
                    join_attrs = {**resource_attr, **scp_attr, **span_attrs}
                    span_obj = Span(
                        trace_id=bytes_to_hex_str(span.trace_id),
                        span_id=bytes_to_hex_str(span.span_id),
                        parent_span_id=bytes_to_hex_str(span.parent_span_id) if span.parent_span_id else None,
                        start_time=datetime.fromtimestamp(span.start_time_unix_nano / 1e9, tz=UTC),
                        end_time=datetime.fromtimestamp(span.end_time_unix_nano / 1e9, tz=UTC),
                        name=span.name,
                        status=span.status.code,
                        attributes=join_attrs,
                        state=span.trace_state,
                    )
                    span_objs.append(span_obj)
                    for event_id, event in enumerate(span.events):
                        # print(f"event name: {event.name}")
                        # print(f"event time: {event.time_unix_nano}")
                        # print(f"attributes: {event.attributes}")
                        event_attrs = normalize_attributes(event.attributes)

                        event_obj = Event(
                            trace_id=bytes_to_hex_str(span.trace_id),
                            span_id=bytes_to_hex_str(span.span_id),
                            event_no=event_id,
                            time=datetime.fromtimestamp(event.time_unix_nano / 1e9, tz=UTC),
                            name=event.name,
                            attributes=event_attrs,
                        )
                        event_objs.append(event_obj)
        print(f"span_objs: {len(span_objs)}")
        print(f"event_objs: {len(event_objs)}")
        async with self.sessionmaker() as session:
            session: AsyncSession
            session.add_all(span_objs)
            session.add_all(event_objs)
            await session.commit()
            # await session.flush()
            # res = await session.execute(text("SELECT 1;"))
            # print(res.scalar())
        return ExportTraceServiceResponse()


@asynccontextmanager
async def db_setup():
    conn_str = os.getenv("APP_DB", "postgres:postgres@localhost:5432/postgres")
    sa_url = "postgresql+psycopg://" + conn_str
    engine = create_async_engine(sa_url)
    sessionmaker = async_sessionmaker(engine, class_=AsyncSession)

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception:
        print("Looks like the table already exists")
    yield sessionmaker
    await engine.dispose()


async def serve():
    async with db_setup() as sessionmaker:
        server = grpc.aio.server()
        add_TraceServiceServicer_to_server(TraceService(sessionmaker), server)
        add_LogsServiceServicer_to_server(LogService(sessionmaker), server)
        SERVICE_NAMES = (
            TRACE_DESCRIPTOR.services_by_name["TraceService"].full_name,
            LOGS_DESCRIPTOR.services_by_name["LogsService"].full_name,
            reflection.SERVICE_NAME,
        )
        reflection.enable_server_reflection(SERVICE_NAMES, server)

        port = os.getenv("APP_PORT", "4317")

        server.add_insecure_port(f"[::]:{port}")
        await server.start()
        print(f"gRPC Server started on port {port}")
        await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(serve())
