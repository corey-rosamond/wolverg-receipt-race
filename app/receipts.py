"""Terminal-receipt recording.

A stage writes ``done`` when it finishes; the watchdog writes ``timeout`` when it
overruns. Both paths funnel through :func:`record_receipt`, which must leave
exactly one receipt per stage execution.

The read is only a fast path. The decision is made by the database: a unique
constraint on ``receipts.stage_execution_id`` means at most one contender's
INSERT commits, and the loser re-reads the winner's row instead of inserting a
second one. That holds across processes, across a restart, and between the
worker and the watchdog — which a ``threading.Lock`` alone does not, because
two instances of the app are exactly the case a rolling deploy produces.
"""

from __future__ import annotations

from typing import Callable

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import Receipt

# Test seam. When set, it is called between the read and the write so a test can
# hold two contenders at exactly the interleaving it wants to prove. It is None in
# production, where the two calls are simply adjacent.
after_check: Callable[[], None] | None = None


def find_receipt(session: Session, stage_execution_id: int) -> Receipt | None:
    return session.scalar(
        select(Receipt).where(Receipt.stage_execution_id == stage_execution_id)
    )


def record_receipt(session: Session, stage_execution_id: int, kind: str) -> Receipt:
    """Record the terminal receipt for a stage, returning the one that stands."""
    existing = find_receipt(session, stage_execution_id)
    if existing is not None:
        return existing

    if after_check is not None:
        after_check()

    receipt = Receipt(stage_execution_id=stage_execution_id, kind=kind)
    session.add(receipt)
    try:
        session.commit()
    except IntegrityError:
        # Another contender committed the terminal receipt first. Theirs stands.
        session.rollback()
        existing = find_receipt(session, stage_execution_id)
        if existing is None:  # pragma: no cover - the constraint was not the cause
            raise
        return existing
    return receipt