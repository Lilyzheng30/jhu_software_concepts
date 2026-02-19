"""Tests for SQLi-safe applicants API behavior."""

import importlib
import os
import sys

import pytest

SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

app_mod = importlib.import_module("app")


class FakeCursor:
    """Cursor double that records SQL execution calls."""

    def __init__(self):
        self.calls = []

    def execute(self, statement, params):
        """Record composed statement object and bound params."""
        self.calls.append((statement, params))

    def fetchall(self):
        """Return one deterministic applicants row."""
        return [
            (
                "Computer Science",
                "Test University",
                "https://example.com/a",
                "Accepted on 1 Jan",
                "Fall 2026",
                "American",
                "Masters",
                3.9,
            )
        ]

    def close(self):
        """No-op close method."""
        return None


class FakeConnection:
    """Connection double returning the fake cursor."""

    def __init__(self):
        self.cur = FakeCursor()

    def cursor(self):
        """Return fake cursor."""
        return self.cur

    def close(self):
        """No-op close method."""
        return None


@pytest.mark.web
def test_clamp_limit_bounds():
    """Limit is clamped to 1..100 and defaults when invalid."""
    assert app_mod.clamp_limit("9999") == 100
    assert app_mod.clamp_limit("-5") == 1
    assert app_mod.clamp_limit("abc") == app_mod.DEFAULT_QUERY_LIMIT


@pytest.mark.web
def test_api_applicants_handles_malicious_input(monkeypatch):
    """Route should bind attacker strings as params and clamp limit."""
    fake_conn = FakeConnection()

    def fake_get_db_connection():
        return fake_conn

    monkeypatch.setattr(app_mod, "get_db_connection", fake_get_db_connection)
    client = app_mod.app.test_client()
    resp = client.get(
        "/api/applicants?program=' OR 1=1 --"
        "&sort_by=program;DROP TABLE applicants;--"
        "&sort_dir=desc;DROP TABLE applicants;--"
        "&limit=10000"
    )
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["ok"] is True
    assert payload["limit"] == 100
    assert len(payload["rows"]) == 1

    executed = fake_conn.cur.calls
    assert executed
    _statement, params = executed[0]
    assert params[0] == "%' OR 1=1 --%"
    assert params[-1] == 100

