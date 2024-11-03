from typing import List, Optional
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKeyConstraint,
    Integer,
    PrimaryKeyConstraint,
    String,
    Text,
)
from sqlalchemy import (
    Uuid as sa_Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Span(Base):
    __tablename__ = "span"

    trace_id: Mapped[str] = mapped_column(String(32))
    span_id: Mapped[str] = mapped_column(String(16))
    parent_span_id: Mapped[Optional[str]] = mapped_column(String(16))
    start_time: Mapped[DateTime] = mapped_column(TIMESTAMP(timezone=False, precision=9))
    end_time: Mapped[DateTime] = mapped_column(TIMESTAMP(timezone=False, precision=9))
    name: Mapped[str] = mapped_column(String)
    status: Mapped[int] = mapped_column(Integer)
    attributes: Mapped[dict] = mapped_column(JSONB)
    state: Mapped[str] = mapped_column(Text)
    events: Mapped[List["Event"]] = relationship("Event")

    __table_args__ = (PrimaryKeyConstraint(trace_id, span_id),)


class Event(Base):
    __tablename__ = "event"

    trace_id: Mapped[str] = mapped_column(String(32))
    span_id: Mapped[str] = mapped_column(String(16))
    event_no: Mapped[int] = mapped_column(Integer)
    time: Mapped[DateTime] = mapped_column(TIMESTAMP(timezone=False, precision=9))
    name: Mapped[str] = mapped_column(String)
    attributes: Mapped[dict] = mapped_column(JSONB)

    __table_args__ = (
        PrimaryKeyConstraint(trace_id, span_id, event_no),
        ForeignKeyConstraint(
            [trace_id, span_id],
            [Span.trace_id, Span.span_id],
            ondelete="CASCADE",
        ),
    )

    __mapper_args__ = {"primary_key": [trace_id, span_id, event_no]}


class Log(Base):
    __tablename__ = "log"

    trace_id: Mapped[str] = mapped_column(String(32))
    span_id: Mapped[str] = mapped_column(String(16))
    log_id: Mapped[UUID] = mapped_column(sa_Uuid)
    severity: Mapped[str] = mapped_column(String(10))
    time: Mapped[DateTime] = mapped_column(TIMESTAMP(timezone=False, precision=9))
    attributes: Mapped[dict] = mapped_column(JSONB)
    body: Mapped[Optional[str]] = mapped_column(Text)

    __mapper_args__ = {"primary_key": [trace_id, span_id, time]}
