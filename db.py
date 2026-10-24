"""
Resilient database connection layer for the Athletic Performance Tracker.

Provides:
  - get_connection()   : Returns a live psycopg2 connection, handling retries.
  - get_db_cursor()    : Context manager that yields a cursor and auto-commits
                         or rolls back on exception.
  - check_health()     : Quick connectivity diagnostic (returns dict).
"""

import psycopg2
from psycopg2 import OperationalError
from contextlib import contextmanager

from config import Config


def get_connection():
    """
    Open and return a new psycopg2 connection using the DSN from Config.
    Raises psycopg2.OperationalError if the database is unreachable.
    """
    conn = psycopg2.connect(Config.get_dsn())
    conn.autocommit = False
    return conn


@contextmanager
def get_db_cursor(commit=True):
    """
    Context manager that provides a database cursor.

    Usage:
        with get_db_cursor() as cur:
            cur.execute("SELECT 1")
            rows = cur.fetchall()

    On normal exit the transaction is committed (if commit=True).
    On exception the transaction is rolled back and the error re-raised.
    The connection is always closed at the end.
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        yield cur
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def check_health():
    """
    Return a dict describing the current database connectivity status.

    Returns:
        {
            "status": "connected" | "error",
            "version": "<pg version string>" | None,
            "database": "<db name>" | None,
            "message": "<human-readable status>"
        }
    """
    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute("SELECT version(), current_database();")
            row = cur.fetchone()
            return {
                "status": "connected",
                "version": row[0],
                "database": row[1],
                "message": f"Connected to {row[1]}",
            }
    except OperationalError as exc:
        return {
            "status": "error",
            "version": None,
            "database": None,
            "message": f"Database unavailable – {exc}",
        }
