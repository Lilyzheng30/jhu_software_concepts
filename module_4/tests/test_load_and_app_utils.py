import os
import sys
import json
import pytest

SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

import load_data
import app


class _Cursor:
    def __init__(self, fetchone_value=None, fetchall_value=None):
        self.queries = []
        self.fetchone_value = fetchone_value
        self.fetchall_value = fetchall_value or []

    def execute(self, query):
        self.queries.append(query)

    def fetchone(self):
        return self.fetchone_value

    def fetchall(self):
        return list(self.fetchall_value)

    def close(self):
        return None


class _Conn:
    def __init__(self, cursor):
        self._cursor = cursor
        self.autocommit = False

    def cursor(self):
        return self._cursor

    def close(self):
        return None


@pytest.mark.db
def test_parse_date_and_float():
    assert load_data.parse_date("January 02, 2025") is not None
    assert load_data.parse_date("2025-01-02") is not None
    assert load_data.parse_date("") is None
    assert load_data.parse_date("bad-date") is None
    assert load_data.parse_float("") is None
    assert load_data.parse_float(None) is None
    assert load_data.parse_float("3.5") == 3.5


@pytest.mark.db
def test_fetch_one_value():
    cur = _Cursor(fetchone_value=(7,))
    assert app.fetch_one_value(cur, "SELECT 7") == 7


@pytest.mark.db
def test_fetch_existing_urls(monkeypatch):
    cur = _Cursor(fetchall_value=[("u1",), ("u2",), (None,)])
    conn = _Conn(cur)
    monkeypatch.setattr(app, "get_db_connection", lambda: conn)
    urls = app.fetch_existing_urls()
    assert urls == {"u1", "u2"}


@pytest.mark.db
def test_merge_out_into_module2_out(tmp_path, monkeypatch):
    base_dir = tmp_path
    master = base_dir / "module_2_out.json"
    batch = base_dir / "out.json"

    master.write_text(json.dumps([{"url": "u1"}]))
    batch.write_text(json.dumps([{"url": "u1"}, {"url": "u2"}]))

    monkeypatch.setattr(app, "os", app.os)
    monkeypatch.setattr(app, "__file__", str(base_dir / "app.py"))

    added, total = app.merge_out_into_module2_out()
    assert added == 1
    assert total == 2


@pytest.mark.db
def test_merge_out_into_module2_out_skip_non_dict(tmp_path, monkeypatch):
    base_dir = tmp_path
    master = base_dir / "module_2_out.json"
    batch = base_dir / "out.json"

    master.write_text(json.dumps([{"url": "u1"}]))
    batch.write_text(json.dumps([{"url": "u2"}, "bad-row"]))

    monkeypatch.setattr(app, "__file__", str(base_dir / "app.py"))

    added, total = app.merge_out_into_module2_out()
    assert added == 1
    assert total == 2


@pytest.mark.web
def test_home_status_message(monkeypatch):
    class DummyCursor:
        def __init__(self):
            self.calls = 0
        def execute(self, _):
            self.calls += 1
        def fetchone(self):
            if self.calls == 3:
                return (0.0, 0.0, 0.0, 0.0)
            return (0,)
        def close(self):
            return None

    class DummyConn:
        def cursor(self):
            return DummyCursor()
        def close(self):
            return None

    monkeypatch.setattr(app, "get_db_connection", lambda: DummyConn())
    monkeypatch.setattr(app, "ensure_initial_dataset_loaded", lambda: True)

    client = app.app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    assert "initial data was loaded" in resp.get_data(as_text=True).lower()


@pytest.mark.db
def test_merge_out_into_module2_out_no_master(tmp_path, monkeypatch):
    base_dir = tmp_path
    batch = base_dir / "out.json"
    batch.write_text(json.dumps([{"url": "u1"}]))

    monkeypatch.setattr(app, "__file__", str(base_dir / "app.py"))

    added, total = app.merge_out_into_module2_out()
    assert added == 1
    assert total == 1


@pytest.mark.db
def test_ensure_initial_dataset_loaded_seeds(monkeypatch):
    cur = _Cursor(fetchone_value=(0,))
    conn = _Conn(cur)
    monkeypatch.setattr(app, "get_db_connection", lambda: conn)
    called = {"ok": False}

    def fake_run_load(**_):
        called["ok"] = True

    monkeypatch.setattr(app, "run_load", fake_run_load)
    seeded = app.ensure_initial_dataset_loaded()
    assert seeded is True
    assert called["ok"] is True


@pytest.mark.db
def test_ensure_initial_dataset_loaded_exception(monkeypatch):
    def fake_conn():
        raise Exception("db down")

    monkeypatch.setattr(app, "get_db_connection", fake_conn)
    called = {"ok": False}

    def fake_run_load(**_):
        called["ok"] = True

    monkeypatch.setattr(app, "run_load", fake_run_load)
    seeded = app.ensure_initial_dataset_loaded()
    assert seeded is True
    assert called["ok"] is True


@pytest.mark.db
def test_create_connection_and_execute_query_error(monkeypatch):
    class FakeCursor:
        def execute(self, _):
            raise load_data.OperationalError("boom")

    class FakeConn:
        def __init__(self):
            self.autocommit = False
        def cursor(self):
            return FakeCursor()

    def fake_connect(**_):
        return FakeConn()

    monkeypatch.setattr(load_data.psycopg, "connect", fake_connect)
    conn = load_data.create_connection("db", "user", "pw", "host", "5432")
    assert conn is not None

    load_data.execute_query(conn, "SELECT 1")


@pytest.mark.db
def test_create_connection_failure(monkeypatch):
    def fake_connect(**_):
        raise load_data.OperationalError("boom")

    monkeypatch.setattr(load_data.psycopg, "connect", fake_connect)
    conn = load_data.create_connection("db", "user", "pw", "host", "5432")
    assert conn is None


@pytest.mark.db
def test_create_database_success(monkeypatch):
    class FakeCursor:
        def execute(self, _):
            return None

    class FakeConn:
        def __init__(self):
            self.autocommit = False
        def cursor(self):
            return FakeCursor()

    conn = FakeConn()
    load_data.create_database(conn, "CREATE DATABASE testdb")


@pytest.mark.db
def test_run_load_main(monkeypatch, tmp_path):
    import runpy

    class FakeCursor:
        def execute(self, *_):
            return None
        def close(self):
            return None

    class FakeConn:
        def __init__(self):
            self.autocommit = False
        def cursor(self):
            return FakeCursor()
        def commit(self):
            return None
        def close(self):
            return None

    def fake_connect(**_):
        return FakeConn()

    monkeypatch.setattr(load_data.psycopg, "connect", fake_connect)
    monkeypatch.setattr(load_data.json, "load", lambda f: [{"url": "u1"}])
    monkeypatch.chdir(tmp_path)

    # Create placeholder file for module_2_out.json
    (tmp_path / "module_2_out.json").write_text("[]")

    runpy.run_module("load_data", run_name="__main__")
