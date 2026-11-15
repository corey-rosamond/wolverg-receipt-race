"""Terminal-receipt recording.

A stage writes ``done`` when it finishes; the watchdog writes ``timeout`` when it
overruns. Both paths funnel through :func:`record_receipt`, which must leave
exactly one receipt per stage execution.

The write path is a check-then-write: it reads for an existing receipt and, if
there is none, inserts one. The read and the insert are not atomic with respect
to each other.
"""

from __future__ import annotations

from typing import Callable

from sqlalchemy import select
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
    session.commit()
    return receipt