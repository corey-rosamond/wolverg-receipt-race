"""Engine and session plumbing.

``DATABASE_URL`` selects the backend; SQLite is the default so the suite runs
with no services. CI runs the same suite twice, once on SQLite and once on
PostgreSQL 16.
"""

from __future__ import annotations

import os

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

DEFAULT_SQLITE = "sqlite+pysqlite:////tmp/wolverg_receipts.db"


def database_url() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_SQLITE)


def make_engine(url: str | None = None) -> Engine:
    url = url or database_url()
    connect_args: dict[str, object] = {}
    if url.startswith("sqlite"):
        # The race is between threads, so the connection must cross threads.
        connect_args = {"check_same_thread": False, "timeout": 30}

    engine = create_engine(url, future=True, connect_args=connect_args)

    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _sqlite_pragmas(dbapi_connection, _record):  # pragma: no cover
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)