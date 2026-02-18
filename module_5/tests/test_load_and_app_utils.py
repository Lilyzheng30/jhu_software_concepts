"""Tests for load_data helpers and app utility functions."""

import importlib
import json
import os
import runpy
import sys

import pytest

SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

load_data = importlib.import_module("load_data")
app_mod = importlib.import_module("app")


def _app_attr(name):
    """Return a callable/object attribute from the app module."""
    return getattr(app_mod, name)


class _Cursor:
    """Minimal cursor double with configurable fetch behavior."""

    def __init__(self, fetchone_value=None, fetchall_value=None):
        """Store responses and track executed SQL strings."""
        self.queries = []
        self.fetchone_value = fetchone_value
        self.fetchall_value = fetchall_value or []

    def execute(self, query):
        """Record executed SQL text."""
        self.queries.append(query)

    def fetchone(self):
        """Return configured single-row response."""
        return self.fetchone_value

    def fetchall(self):
        """Return configured multi-row response."""
        return list(self.fetchall_value)

    def close(self):
        """No-op close method."""
        return None


class _Conn:
    """Minimal connection double returning a fixed cursor."""

    def __init__(self, cursor):
        """Create connection with a prebuilt cursor."""
        self._cursor = cursor
        self.autocommit = False

    def cursor(self):
        """Return the held cursor."""
        return self._cursor

    def close(self):
        """No-op close method."""
        return None


@pytest.mark.db
def test_parse_date_and_float():
    """Date and float parsers handle valid and invalid values."""
    assert load_data.parse_date("January 02, 2025") is not None
    assert load_data.parse_date("2025-01-02") is not None
    assert load_data.parse_date("") is None
    assert load_data.parse_date("bad-date") is None
    assert load_data.parse_float("") is None
    assert load_data.parse_float(None) is None
    assert load_data.parse_float("3.5") == 3.5


@pytest.mark.db
def test_fetch_one_value():
    """fetch_one_value executes a query and returns first scalar."""
    cur = _Cursor(fetchone_value=(7,))
    assert _app_attr("fetch_one_value")(cur, "SELECT 7") == 7


@pytest.mark.db
def test_fetch_existing_urls(monkeypatch):
    """fetch_existing_urls returns only non-null URL values."""
    cur = _Cursor(fetchall_value=[("u1",), ("u2",), (None,)])
    conn = _Conn(cur)

    def _fake_conn():
        return conn

    monkeypatch.setattr(app_mod, "get_db_connection", _fake_conn)
    urls = _app_attr("fetch_existing_urls")()
    assert urls == {"u1", "u2"}


@pytest.mark.db
def test_get_db_connection_uses_database_url(monkeypatch):
    """get_db_connection uses DATABASE_URL env var when available."""
    called = {"url": None}

    def _fake_connect(arg):
        called["url"] = arg
        return "conn"

    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h:5432/db")
    monkeypatch.setattr(app_mod.psycopg, "connect", _fake_connect)

    conn = _app_attr("get_db_connection")()
    assert conn == "conn"
    assert called["url"] == "postgresql://u:p@h:5432/db"


@pytest.mark.db
def test_get_db_connection_missing_database_url(monkeypatch):
    """Missing DATABASE_URL raises RuntimeError."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError):
        _app_attr("get_db_connection")()


@pytest.mark.db
def test_merge_out_into_module2_out(tmp_path, monkeypatch):
    """Merge out.json into module_2_out.json and add only new URLs."""
    base_dir = tmp_path
    master = base_dir / "module_2_out.json"
    batch = base_dir / "out.json"

    master.write_text(json.dumps([{"url": "u1"}]))
    batch.write_text(json.dumps([{"url": "u1"}, {"url": "u2"}]))

    monkeypatch.setattr(app_mod, "__file__", str(base_dir / "app.py"))

    added, total = _app_attr("merge_out_into_module2_out")()
    assert added == 1
    assert total == 2


@pytest.mark.db
def test_merge_out_into_module2_out_skip_non_dict(tmp_path, monkeypatch):
    """Skip non-dict entries while merging out.json rows."""
    base_dir = tmp_path
    master = base_dir / "module_2_out.json"
    batch = base_dir / "out.json"

    master.write_text(json.dumps([{"url": "u1"}]))
    batch.write_text(json.dumps([{"url": "u2"}, "bad-row"]))

    monkeypatch.setattr(app_mod, "__file__", str(base_dir / "app.py"))

    added, total = _app_attr("merge_out_into_module2_out")()
    assert added == 1
    assert total == 2


@pytest.mark.web
def test_home_status_message(monkeypatch):
    """Home page shows initial-load status message when seeded."""

    class _DummyCursor:
        """Cursor double returning expected query results."""

        def __init__(self):
            """Initialize call counter."""
            self.calls = 0

        def execute(self, _query):
            """Track executed query count."""
            self.calls += 1

        def fetchone(self):
            """Return q3-shaped tuple on third query and scalar otherwise."""
            if self.calls == 3:
                return (0.0, 0.0, 0.0, 0.0)
            return (0,)

        def close(self):
            """No-op close method."""
            return None

    class _DummyConn:
        """Connection double returning DummyCursor."""

        def cursor(self):
            """Return dummy cursor."""
            return _DummyCursor()

        def close(self):
            """No-op close method."""
            return None

    def _fake_conn():
        return _DummyConn()

    def _fake_seed():
        return True

    monkeypatch.setattr(app_mod, "get_db_connection", _fake_conn)
    monkeypatch.setattr(app_mod, "ensure_initial_dataset_loaded", _fake_seed)

    client = app_mod.app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    assert "initial data was loaded" in resp.get_data(as_text=True).lower()


@pytest.mark.db
def test_merge_out_into_module2_out_no_master(tmp_path, monkeypatch):
    """Merging works when master file does not exist yet."""
    base_dir = tmp_path
    batch = base_dir / "out.json"
    batch.write_text(json.dumps([{"url": "u1"}]))

    monkeypatch.setattr(app_mod, "__file__", str(base_dir / "app.py"))

    added, total = _app_attr("merge_out_into_module2_out")()
    assert added == 1
    assert total == 1


@pytest.mark.db
def test_ensure_initial_dataset_loaded_seeds(monkeypatch):
    """Seeding runs when applicant count is zero."""
    cur = _Cursor(fetchone_value=(0,))
    conn = _Conn(cur)

    def _fake_conn():
        return conn

    called = {"ok": False}

    def _fake_run_load(**_kwargs):
        called["ok"] = True

    monkeypatch.setattr(app_mod, "get_db_connection", _fake_conn)
    monkeypatch.setattr(app_mod, "run_load", _fake_run_load)

    seeded = _app_attr("ensure_initial_dataset_loaded")()
    assert seeded is True
    assert called["ok"] is True


@pytest.mark.db
def test_ensure_initial_dataset_loaded_exception(monkeypatch):
    """Seeding still runs when connection creation fails."""

    def _fake_conn():
        raise RuntimeError("db down")

    called = {"ok": False}

    def _fake_run_load(**_kwargs):
        called["ok"] = True

    monkeypatch.setattr(app_mod, "get_db_connection", _fake_conn)
    monkeypatch.setattr(app_mod, "run_load", _fake_run_load)

    seeded = _app_attr("ensure_initial_dataset_loaded")()
    assert seeded is True
    assert called["ok"] is True


@pytest.mark.db
def test_ensure_initial_dataset_loaded_cursor_error(monkeypatch):
    """Seeding runs when cursor query fails."""

    class _BadCursor:
        """Cursor that fails on execute."""

        def execute(self, _query):
            """Raise runtime error for execute path."""
            raise RuntimeError("cursor fail")

        def fetchone(self):
            """Return fallback count tuple."""
            return (1,)

        def close(self):
            """No-op close method."""
            return None

    class _BadConn:
        """Connection returning a failing cursor."""

        def cursor(self):
            """Return failing cursor."""
            return _BadCursor()

        def close(self):
            """No-op close method."""
            return None

    called = {"ok": False}

    def _fake_run_load(**_kwargs):
        called["ok"] = True

    def _fake_conn_bad():
        """Return bad connection for error branch tests."""
        return _BadConn()

    monkeypatch.setattr(app_mod, "get_db_connection", _fake_conn_bad)
    monkeypatch.setattr(app_mod, "run_load", _fake_run_load)

    seeded = _app_attr("ensure_initial_dataset_loaded")()
    assert seeded is True
    assert called["ok"] is True


@pytest.mark.db
def test_create_connection_and_execute_query_error(monkeypatch):
    """create_connection returns conn and execute_query handles failures."""

    class _FakeCursor:
        """Cursor that always raises OperationalError."""

        def execute(self, _query):
            """Raise OperationalError for execute_query error path."""
            raise load_data.OperationalError("boom")

        def close(self):
            """No-op close method."""
            return None

    class _FakeConn:
        """Connection returning failing cursor."""

        def __init__(self):
            self.autocommit = False

        def cursor(self):
            """Return failing cursor."""
            return _FakeCursor()

        def close(self):
            """No-op close method."""
            return None

    def _fake_connect(**_kwargs):
        return _FakeConn()

    monkeypatch.setattr(load_data.psycopg, "connect", _fake_connect)
    conn = load_data.create_connection("db", "user", "pw", "host", "5432")
    assert conn is not None

    load_data.execute_query(conn, "SELECT 1")


@pytest.mark.db
def test_create_connection_failure(monkeypatch):
    """create_connection returns None on OperationalError."""

    def _fake_connect(**_kwargs):
        raise load_data.OperationalError("boom")

    monkeypatch.setattr(load_data.psycopg, "connect", _fake_connect)
    conn = load_data.create_connection("db", "user", "pw", "host", "5432")
    assert conn is None


@pytest.mark.db
def test_create_database_success():
    """create_database executes SQL against provided connection."""

    class _FakeCursor:
        """Cursor that accepts execute calls."""

        def execute(self, _query):
            """Accept any SQL query."""
            return None

        def close(self):
            """No-op close method."""
            return None

    class _FakeConn:
        """Connection returning fake cursor."""

        def __init__(self):
            self.autocommit = False

        def cursor(self):
            """Return fake cursor."""
            return _FakeCursor()

        def close(self):
            """No-op close method."""
            return None

    conn = _FakeConn()
    load_data.create_database(conn, "CREATE DATABASE testdb")


@pytest.mark.db
def test_run_load_main(monkeypatch, tmp_path):
    """load_data __main__ path runs with mocked DB and JSON load."""

    class _FakeCursor:
        """Cursor double for the run_load main flow."""

        def execute(self, *_args):
            """Accept execute calls during run_load flow."""
            return None

        def close(self):
            """No-op close method."""
            return None

    class _FakeConn:
        """Connection double for the run_load main flow."""

        def __init__(self):
            self.autocommit = False

        def cursor(self):
            """Return fake cursor."""
            return _FakeCursor()

        def commit(self):
            """No-op commit method."""
            return None

        def close(self):
            """No-op close method."""
            return None

    def _fake_connect(**_kwargs):
        return _FakeConn()

    def _fake_json_load(_file_obj):
        return [{"url": "u1"}]

    monkeypatch.setattr(load_data.psycopg, "connect", _fake_connect)
    monkeypatch.setattr(load_data.json, "load", _fake_json_load)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "module_2_out.json").write_text("[]")

    runpy.run_module("load_data", run_name="__main__")
