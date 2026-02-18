"""Tests query_data helpers and __main__ output path."""

import importlib
import os
import runpy
import sys

import pytest

SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

query_data = importlib.import_module("query_data")


class _FakeCursor:
    """Simple cursor double for read-query tests."""

    def __init__(self, rows=None):
        """Store rows and executed SQL."""
        self.rows = rows or [(1,)]
        self.executed = []

    def execute(self, query):
        """Record SQL query text."""
        self.executed.append(query)

    def fetchall(self):
        """Return configured result rows."""
        return list(self.rows)


class _FakeConn:
    """Simple connection double returning one cursor."""

    def __init__(self, rows=None):
        """Create inner cursor with optional rows."""
        self.cursor_obj = _FakeCursor(rows=rows)
        self.autocommit = False

    def cursor(self):
        """Return test cursor."""
        return self.cursor_obj

    def close(self):
        """No-op close method for compatibility."""
        return None


@pytest.mark.db
def test_execute_read_query_returns_rows():
    """execute_read_query returns rows from cursor.fetchall."""
    conn = _FakeConn(rows=[(5,)])
    rows = query_data.execute_read_query(conn, "SELECT 5;")
    assert rows == [(5,)]


@pytest.mark.db
def test_execute_read_query_none_connection():
    """execute_read_query returns None when connection is missing."""
    assert query_data.execute_read_query(None, "SELECT 1;") is None


@pytest.mark.db
def test_create_connection_failure(monkeypatch):
    """create_connection returns None when psycopg connect fails."""

    def _fake_connect(**_kwargs):
        raise query_data.OperationalError("boom")

    monkeypatch.setattr(query_data.psycopg, "connect", _fake_connect)
    conn = query_data.create_connection("db", "user", "pw", "host", "5432")
    assert conn is None


@pytest.mark.db
def test_execute_read_query_exception():
    """execute_read_query handles cursor exceptions and returns None."""

    class _BadCursor:
        """Cursor that fails in execute."""

        def execute(self, _query):
            """Raise an OperationalError for execute path testing."""
            raise query_data.OperationalError("boom")

        def fetchall(self):
            """Return empty row list."""
            return []

    class _BadConn:
        """Connection returning a failing cursor."""

        def __init__(self):
            self.autocommit = False

        def cursor(self):
            """Return failing cursor."""
            return _BadCursor()

        def close(self):
            """No-op close method for compatibility."""
            return None

    rows = query_data.execute_read_query(_BadConn(), "SELECT 1;")
    assert rows is None


@pytest.mark.db
def test_query_data_main_runs(monkeypatch, capsys):
    """Running query_data as __main__ prints expected labels."""

    class _MainCursor:
        """Cursor for __main__ branch with q3-specific tuple length."""

        def __init__(self):
            self.executed = []

        def execute(self, query):
            """Track query text in execution order."""
            self.executed.append(query)

        def fetchall(self):
            """Return q3-shape tuple or scalar tuple based on query text."""
            if self.executed and "AVG(" in self.executed[-1]:
                return [(1, 2, 3, 4)]
            return [(1,)]

    class _MainConn:
        """Connection for __main__ branch."""

        def __init__(self):
            self.autocommit = False
            self._cursor = _MainCursor()

        def cursor(self):
            """Return prepared cursor instance."""
            return self._cursor

        def close(self):
            """No-op close method."""
            return None

    def _fake_connect(**_kwargs):
        return _MainConn()

    monkeypatch.setattr(query_data.psycopg, "connect", _fake_connect)

    runpy.run_module("query_data", run_name="__main__")
    out = capsys.readouterr().out
    assert "Applicant count:" in out


@pytest.mark.db
def test_first_value_none_path():
    """first_value helper returns None when no rows are returned."""
    globals_dict = runpy.run_module("query_data", run_name="__main__")

    def _fake_execute_read_query(_conn, _query):
        return []

    globals_dict["execute_read_query"] = _fake_execute_read_query
    globals_dict["connection"] = object()
    assert globals_dict["first_value"]("SELECT 1") is None
