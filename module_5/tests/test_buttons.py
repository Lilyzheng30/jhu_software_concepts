"""Tests pull/update button endpoints and busy-state gating."""

import importlib
import os
import sys

import pytest

SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)


@pytest.fixture(name="app_fixture")
def fixture_app():
    """Return imported app module for endpoint testing."""
    return importlib.import_module("app")


@pytest.mark.buttons
def test_post_pull_data_triggers_pipeline(app_fixture, monkeypatch):
    """POST /api/pull-data should trigger pipeline call."""
    called = {"ok": False}

    def _fake_run_pull():
        called["ok"] = True
        return True, "ok", False

    monkeypatch.setattr(app_fixture, "run_pull_data_pipeline", _fake_run_pull)

    client = app_fixture.app.test_client()
    resp = client.post("/api/pull-data")
    assert resp.status_code == 200
    assert called["ok"] is True


@pytest.mark.buttons
def test_post_update_analysis_not_busy(app_fixture):
    """POST /api/update-analysis succeeds when not busy."""
    app_fixture.is_pulling = False
    client = app_fixture.app.test_client()
    resp = client.post("/api/update-analysis")
    assert resp.status_code == 200


@pytest.mark.buttons
def test_busy_gating_blocks_actions(app_fixture):
    """Busy state blocks both update-analysis and pull-data actions."""
    app_fixture.is_pulling = True
    client = app_fixture.app.test_client()

    resp_update = client.post("/api/update-analysis")
    assert resp_update.status_code == 409

    resp_pull = client.post("/api/pull-data")
    assert resp_pull.status_code == 409

    app_fixture.is_pulling = False
