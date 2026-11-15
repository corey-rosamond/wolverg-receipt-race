from __future__ import annotations

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.db import make_engine, make_session_factory
from app.models import Base, StageExecution


@pytest.fixture()
def engine() -> Engine:
    engine = make_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return make_session_factory(engine)


@pytest.fixture()
def stage_id(session_factory: sessionmaker[Session]) -> int:
    with session_factory() as session:
        stage = StageExecution(name="reconciliation")
        session.add(stage)
        session.commit()
        return stage.id