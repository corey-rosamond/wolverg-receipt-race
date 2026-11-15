# Duplicate terminal receipts — reproduction

A pipeline stage writes a `done` receipt when it finishes. A watchdog thread
writes a `timeout` receipt when the stage overruns. Exactly one receipt may
exist per stage execution — whichever side gets there first.

This repository holds the write path, the schema, and the test that isolates the
race.

## Run

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pytest -q
```

Set `DATABASE_URL` to run against PostgreSQL instead of the default SQLite file:

```bash
DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/db .venv/bin/pytest -q
```

CI runs the suite twice, once on SQLite and once on PostgreSQL 16.

## Layout

| Path | What it is |
| --- | --- |
| `app/models.py` | `stage_executions`, `receipts` |
| `app/receipts.py` | `record_receipt`, the write path both callers use |
| `app/db.py` | engine/session wiring, SQLite and PostgreSQL |
| `tests/test_receipts.py` | the suite |
| `.github/workflows/ci.yml` | SQLite and PostgreSQL jobs |