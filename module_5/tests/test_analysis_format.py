"""Tests analysis page labels and percentage formatting output."""

import importlib
import os
import sys

import pytest

SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)


class _FormatCursor:
    """Cursor double returning fixed values for analysis queries."""

    def __init__(self):
        """Initialize call counter."""
        self.calls = 0

    def execute(self, _query):
        """Track how many queries were executed."""
        self.calls += 1

    def fetchone(self):
        """Return tuples expected by the page rendering logic."""
        if self.calls == 3:
            return (3.45, 320.12, 160.34, 4.56)
        if self.calls == 2:
            return (12.34,)
        if self.calls == 5:
            return (56.78,)
        return (1,)

    def close(self):
        """No-op close implementation."""
        return None


class _FormatConn:
    """Connection double returning a format cursor."""

    def cursor(self):
        """Return a fresh cursor instance."""
        return _FormatCursor()

    def close(self):
        """No-op close implementation."""
        return None


@pytest.fixture(name="app_fixture")
def fixture_app(monkeypatch):
    """Provide app module with DB and seed behavior monkeypatched."""
    app_module = importlib.import_module("app")

    def _fake_conn():
        return _FormatConn()

    def _fake_seed():
        return False

    monkeypatch.setattr(app_module, "get_db_connection", _fake_conn)
    monkeypatch.setattr(app_module, "ensure_initial_dataset_loaded", _fake_seed)
    return app_module


@pytest.mark.analysis
def test_labels_and_percentage_format(app_fixture):
    """Analysis page includes labels and formatted percentages."""
    client = app_fixture.app.test_client()
    resp = client.get("/analysis")
    assert resp.status_code == 200

    text = resp.get_data(as_text=True)
    assert "Answer:" in text
    assert "12.34%" in text
    assert "56.78%" in text
