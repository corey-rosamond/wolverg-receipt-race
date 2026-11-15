"""Wolverg receipts — a minimal reproduction of the duplicate-terminal-receipt race.

A pipeline stage writes a ``done`` receipt when it finishes. A watchdog thread
writes a ``timeout`` receipt when the stage overruns. Exactly one receipt may
exist per stage execution, whichever side writes first.
"""

__all__ = ["db", "models", "receipts"]