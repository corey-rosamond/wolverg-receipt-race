"""Tables for stage executions and their terminal receipts."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class StageExecution(Base):
    __tablename__ = "stage_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")

    receipts: Mapped[list["Receipt"]] = relationship(back_populates="stage")


class Receipt(Base):
    __tablename__ = "receipts"
    # One terminal receipt per stage execution, enforced in the database rather
    # than in the caller. Two contenders may both decide to write; the loser's
    # INSERT is rejected here and it re-reads the winner's row.
    __table_args__ = (
        UniqueConstraint("stage_execution_id", name="uq_receipts_stage_execution"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stage_execution_id: Mapped[int] = mapped_column(
        ForeignKey("stage_executions.id"), nullable=False
    )
    # "done" written by the worker, "timeout" written by the watchdog.
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    stage: Mapped[StageExecution] = relationship(back_populates="receipts")