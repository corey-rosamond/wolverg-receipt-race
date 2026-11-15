# Duplicate terminal receipts — reproduction

A pipeline stage writes a `done` receipt when it finishes. A watchdog thread
writes a `timeout` receipt when the stage overruns. Exactly one receipt may exist
per stage execution — whichever side gets there first.

This repository holds the write path, the schema, the test that isolates the race,
and the fix.

## The defect

`record_receipt` is a check-then-write: it reads for an existing receipt and, if
there is none, inserts one. The two statements are not atomic with respect to
each other, so this interleaving is possible:

| | worker | watchdog |
| --- | --- | --- |
| 1 | `SELECT` → no receipt | |
| 2 | | `SELECT` → no receipt |
| 3 | `INSERT done` | |
| 4 | | `INSERT timeout` |

Both callers saw "unfinished", so both write, and the stage has two terminal
receipts.

## The test

`tests/test_duplicate_receipts.py` does not hope for that window, it creates it.
A `threading.Barrier` is placed exactly between the read and the write, so the
test holds both contenders inside the unchecked interval before releasing them.
One run, same result every time — no `sleep()`, no "run it 1,000 times".

On the unfixed code:

```
assert count_receipts(session_factory, stage_id) == 1
E   AssertionError: assert 2 == 1
```

## The fix

The read stays as a fast path, but it no longer decides anything. The database
does:

- `UNIQUE (stage_execution_id)` on `receipts`, so at most one terminal receipt
  can ever be committed;
- the losing `INSERT` raises `IntegrityError`, is rolled back, and re-reads the
  winner's row instead of inserting a second one.

That matters because the failure is not confined to one process. Two instances of
the app overlapping during a rolling deploy — the case that makes the scheduler
fencing problem real — are two processes, and a `threading.Lock` is invisible to
the other one. The constraint is not.

`test_database_rejects_a_second_terminal_receipt` pins the invariant directly:
it inserts a `done` receipt, then asserts a `timeout` insert is rejected, so the
guarantee does not depend on the write path remembering to check.

## Applying it to an existing table

`drop_all`/`create_all` is enough for this reproduction, but adding the
constraint to a live table needs a migration, and it will fail if duplicates
already exist. Order: deploy the constraint and the re-read together; dedupe
`receipts` first if production already has double rows, keeping the earliest per
`stage_execution_id`.

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
| `app/models.py` | `stage_executions`, `receipts`, the unique constraint |
| `app/receipts.py` | `record_receipt`, the write path both callers use |
| `app/db.py` | engine/session wiring, SQLite and PostgreSQL |
| `tests/test_duplicate_receipts.py` | the race, and the constraint backstop |
| `tests/test_receipts.py` | happy path |
| `.github/workflows/ci.yml` | SQLite and PostgreSQL jobs |

## History

- `test: force the worker and watchdog past the receipt check` — adds the test;
  CI red.
- `fix: let the database decide which receipt stands` — adds the constraint and
  the re-read; CI green.