"""The defect, isolated.

The worker writes ``done`` when the stage finishes. The watchdog writes
``timeout`` when it overruns. Both call ``record_receipt``, which reads for an
existing receipt and, finding none, inserts one. If both callers get past the
read before either commits, both insert, and the stage ends up with two
terminal receipts.

The test removes the timing window from the equation: a ``threading.Barrier`` is
placed exactly between the read and the write, so the interleaving is *forced*
rather than hoped for. No ``sleep()``, no repeated runs — one execution, same
result every time.
"""

from __future__ import annotations

import threading

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app import receipts
from app.models import Receipt


def count_receipts(session_factory: sessionmaker, stage_execution_id: int) -> int:
    with session_factory() as session:
        return int(
            session.scalar(
                select(func.count())
                .select_from(Receipt)
                .where(Receipt.stage_execution_id == stage_execution_id)
            )
            or 0
        )


def test_worker_and_watchdog_write_exactly_one_receipt(
    session_factory: sessionmaker, stage_id: int
) -> None:
    both_past_the_read = threading.Barrier(2, timeout=10)
    failures: list[BaseException] = []

    def contend(kind: str) -> None:
        try:
            with session_factory() as session:
                receipts.record_receipt(session, stage_id, kind)
        except BaseException as exc:  # surfaced by the assertion below
            failures.append(exc)

    receipts.after_check = both_past_the_read.wait
    try:
        worker = threading.Thread(target=contend, args=("done",), name="worker")
        watchdog = threading.Thread(target=contend, args=("timeout",), name="watchdog")
        worker.start()
        watchdog.start()
        worker.join(15)
        watchdog.join(15)
    finally:
        receipts.after_check = None

    assert failures == [], failures
    assert count_receipts(session_factory, stage_id) == 1


def test_database_rejects_a_second_terminal_receipt(
    session_factory: sessionmaker, stage_id: int
) -> None:
    """The invariant does not depend on the write path remembering to check."""
    with session_factory() as session:
        session.add(Receipt(stage_execution_id=stage_id, kind="done"))
        session.commit()

    with pytest.raises(IntegrityError):
        with session_factory() as session:
            session.add(Receipt(stage_execution_id=stage_id, kind="timeout"))
            session.commit()