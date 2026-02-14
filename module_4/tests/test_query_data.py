# Tests query helpers and main path behavior.
import os
import sys
import pytest

SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

import query_data


class _FakeCursor:
    def __init__(self, rows=None):
        self.rows = rows or [(1,)]
        self.executed = []

    def execute(self, query):
        self.executed.append(query)

    def fetchall(self):
        return list(self.rows)


class _FakeConn:
    def __init__(self, rows=None):
        self.cursor_obj = _FakeCursor(rows=rows)
        self.autocommit = False

    def cursor(self):
        return self.cursor_obj


@pytest.mark.db
# test_execute_read_query_returns_rows()
def test_execute_read_query_returns_rows():
    conn = _FakeConn(rows=[(5,)])
    rows = query_data.execute_read_query(conn, "SELECT 5;")
    assert rows == [(5,)]


@pytest.mark.db
# test_create_connection_failure(monkeypatch)
def test_create_connection_failure(monkeypatch):
    def fake_connect(**_):
        raise query_data.OperationalError("boom")

    monkeypatch.setattr(query_data.psycopg, "connect", fake_connect)
    conn = query_data.create_connection("db", "user", "pw", "host", "5432")
    assert conn is None


@pytest.mark.db
# test_execute_read_query_exception(monkeypatch)
def test_execute_read_query_exception(monkeypatch):
    class BadCursor:
        def execute(self, _):
            raise query_data.OperationalError("boom")
        def fetchall(self):
            return []

    class BadConn:
        def __init__(self):
            self.autocommit = False
        def cursor(self):
            return BadCursor()

    rows = query_data.execute_read_query(BadConn(), "SELECT 1;")
    assert rows is None


@pytest.mark.db
# test_query_data_main_runs(monkeypatch, capsys)
def test_query_data_main_runs(monkeypatch, capsys):
    import runpy

    class FakeCursor:
        def __init__(self):
            self.executed = []

        def execute(self, query):
            self.executed.append(query)

        def fetchall(self):
            # Return 4 values for q3, else 1 value.
            if self.executed and "AVG(" in self.executed[-1]:
                return [(1, 2, 3, 4)]
            return [(1,)]

    class FakeConn:
        def __init__(self):
            self.autocommit = False
            self._cursor = FakeCursor()

        def cursor(self):
            return self._cursor

        def close(self):
            return None

    def fake_connect(**_):
        return FakeConn()

    monkeypatch.setattr(query_data.psycopg, "connect", fake_connect)

    runpy.run_module("query_data", run_name="__main__")
    out = capsys.readouterr().out
    assert "Applicant count:" in out


@pytest.mark.db
# test_first_value_none_path(monkeypatch)
def test_first_value_none_path(monkeypatch):
    # Run __main__ and then call first_value with empty rows to hit line 132.
    import runpy

    g = runpy.run_module("query_data", run_name="__main__")

    def fake_execute_read_query(conn, query):
        return []

    g["execute_read_query"] = fake_execute_read_query
    g["connection"] = object()
    assert g["first_value"]("SELECT 1") is None
