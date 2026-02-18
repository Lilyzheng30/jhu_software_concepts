"""Tests Flask app creation and analysis page rendering."""

import os
import sys
import importlib

import pytest
from flask import Flask

SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

app_mod = importlib.import_module("app")


class FakeCursor:
    """Minimal cursor fake for deterministic query outputs."""

    def __init__(self):
        self.queries = []
        self.fetchone_values = [
            (0,),  # q1
            (0.0,),  # q2
            (0.0,),  # q4
            (0.0,),  # q5
            (0.0,),  # q6
            (0,),  # q7
            (0,),  # q8
            (0,),  # q9
            (0,),  # q10
            (0.0,),  # q11
        ]
        self.q3_row = (0.0, 0.0, 0.0, 0.0)

    def execute(self, query):
        """Record executed query text."""
        self.queries.append(query)

    def fetchone(self):
        """Return deterministic rows that mirror app query order."""
        if "AVG(gpa)::numeric" in self.queries[-1]:
            return self.q3_row
        if self.fetchone_values:
            return self.fetchone_values.pop(0)
        return None

    def close(self):
        """No-op close to mimic DB cursor API."""
        return None


class FakeConnection:
    """Minimal connection fake returning the cursor stub."""

    def __init__(self):
        self.cursor_obj = FakeCursor()

    def cursor(self):
        """Return cursor fake."""
        return self.cursor_obj

    def close(self):
        """No-op close to mimic DB connection API."""
        return None


@pytest.fixture(name="app_fixture")
def fixture_app(monkeypatch):
    """Return app module with DB dependencies patched out."""
    def fake_get_db_connection():
        return FakeConnection()

    def fake_ensure_initial_dataset_loaded():
        return False

    monkeypatch.setattr(app_mod, "get_db_connection", fake_get_db_connection)
    monkeypatch.setattr(
        app_mod,
        "ensure_initial_dataset_loaded",
        fake_ensure_initial_dataset_loaded,
    )
    return app_mod


@pytest.mark.web
def test_routes_exist(app_fixture):
    """All expected app routes are registered."""
    routes = {rule.rule for rule in app_fixture.app.url_map.iter_rules()}
    assert "/" in routes
    assert "/analysis" in routes
    assert "/pull-data" in routes
    assert "/pull-data-silent" in routes
    assert "/update-analysis" in routes
    assert "/api/pull-data" in routes
    assert "/api/update-analysis" in routes


@pytest.mark.web
def test_create_app(app_fixture):
    """App factory returns a Flask instance."""
    flask_app = app_fixture.create_app()
    assert flask_app is not None
    assert isinstance(flask_app, Flask)


@pytest.mark.web
def test_get_home_page_renders(app_fixture):
    """Analysis page renders key controls and labels."""
    client = app_fixture.app.test_client()
    resp = client.get("/analysis")
    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    assert "Pull Data" in text
    assert "Update Analysis" in text
    assert "Analysis" in text
    assert "Answer:" in text
