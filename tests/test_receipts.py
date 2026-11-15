from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.models import Receipt
from app.receipts import record_receipt


def test_worker_records_one_receipt(session_factory: sessionmaker, stage_id: int) -> None:
    with session_factory() as session:
        record_receipt(session, stage_id, "done")

    with session_factory() as session:
        count = session.scalar(
            select(func.count()).select_from(Receipt).where(
                Receipt.stage_execution_id == stage_id
            )
        )
    assert count == 1