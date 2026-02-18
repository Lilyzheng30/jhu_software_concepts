"""Tests pipeline helpers and handler branches."""

import os
import sys
import json
import runpy
import importlib

import pytest
import flask

SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

app_module = importlib.import_module("app")
llm_app = importlib.import_module("module_2.llm_hosting.app")


@pytest.mark.buttons
def test_run_pull_data_pipeline_busy():
    """Busy flag blocks concurrent pull pipeline runs."""
    app_module.is_pulling = True
    ok, status, seeded = app_module.run_pull_data_pipeline()
    assert ok is False
    assert "already running" in status
    assert seeded is False
    app_module.is_pulling = False


@pytest.mark.buttons
def test_run_pull_data_pipeline_exception(monkeypatch):
    """Scrape exceptions are reported as pull-data failure status."""
    def boom(*_, **__):
        raise RuntimeError("fail")

    monkeypatch.setattr(app_module, "run_scrape", boom)
    app_module.is_pulling = False
    ok, status, _ = app_module.run_pull_data_pipeline()
    assert ok is False
    assert "Pull Data failed" in status


@pytest.mark.buttons
def test_handle_pull_data_redirects(monkeypatch):
    """Pull handler redirects across failure/success seed branches."""
    monkeypatch.setattr(app_module, "run_pull_data_pipeline", lambda: (False, "status", False))
    with app_module.app.test_request_context("/pull-data"):
        resp = app_module.handle_pull_data()
        assert resp.status_code == 302

    monkeypatch.setattr(app_module, "run_pull_data_pipeline", lambda: (True, "ok", True))
    with app_module.app.test_request_context("/pull-data"):
        resp2 = app_module.handle_pull_data()
        assert resp2.status_code == 302

    # ok + not seeded path
    monkeypatch.setattr(app_module, "run_pull_data_pipeline", lambda: (True, "ok", False))
    with app_module.app.test_request_context("/pull-data"):
        resp3 = app_module.handle_pull_data()
        assert resp3.status_code == 302


@pytest.mark.buttons
def test_pull_data_get_redirect():
    """GET pull-data endpoint redirects to analysis page."""
    client = app_module.app.test_client()
    resp = client.get("/pull-data")
    assert resp.status_code == 302


@pytest.mark.buttons
def test_pull_data_silent_success(monkeypatch):
    """Silent pull returns 204 when pipeline succeeds."""
    monkeypatch.setattr(app_module, "run_pull_data_pipeline", lambda: (True, "ok", False))
    client = app_module.app.test_client()
    resp = client.post("/pull-data-silent")
    assert resp.status_code == 204


@pytest.mark.buttons
def test_pull_data_silent_busy(monkeypatch):
    """Silent pull returns 409 when pipeline is busy/fails."""
    monkeypatch.setattr(app_module, "run_pull_data_pipeline", lambda: (False, "busy", False))
    client = app_module.app.test_client()
    resp = client.post("/pull-data-silent")
    assert resp.status_code == 409


@pytest.mark.buttons
def test_update_analysis_get_redirect():
    """GET update-analysis endpoint redirects to analysis page."""
    client = app_module.app.test_client()
    resp = client.get("/update-analysis")
    assert resp.status_code == 302


@pytest.mark.buttons
def test_handle_update_analysis_busy():
    """Update analysis redirects when pull operation is in progress."""
    app_module.is_pulling = True
    with app_module.app.test_request_context("/update-analysis"):
        resp = app_module.handle_update_analysis()
        assert resp.status_code == 302
    app_module.is_pulling = False


@pytest.mark.buttons
def test_handle_update_analysis_not_busy():
    """Update analysis redirects with success status when not busy."""
    app_module.is_pulling = False
    with app_module.app.test_request_context("/update-analysis"):
        resp = app_module.handle_update_analysis()
        assert resp.status_code == 302


@pytest.mark.buttons
def test_pull_data_post_calls_handler(monkeypatch):
    """POST pull-data delegates to handler."""
    monkeypatch.setattr(app_module, "handle_pull_data", lambda: ("ok", 302))
    client = app_module.app.test_client()
    resp = client.post("/pull-data")
    assert resp.status_code == 302


@pytest.mark.buttons
def test_update_analysis_post_calls_handler(monkeypatch):
    """POST update-analysis delegates to handler."""
    monkeypatch.setattr(app_module, "handle_update_analysis", lambda: ("ok", 302))
    client = app_module.app.test_client()
    resp = client.post("/update-analysis")
    assert resp.status_code == 302


@pytest.mark.buttons
def test_run_llm_and_write_out_json(monkeypatch):
    """LLM jsonl output is converted into out.json."""
    # Ensure we run in src so relative paths resolve.
    monkeypatch.chdir(SRC_PATH)

    jsonl_path = os.path.join(SRC_PATH, "module_2", "llm_extend_applicant_data.json.jsonl")

    def fake_cli(*_, **__):
        with open(jsonl_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"url": "u1"}) + "\n")

    monkeypatch.setattr(llm_app, "cli_process_file", fake_cli)
    app_module.run_llm_and_write_out_json()

    out_path = os.path.join(SRC_PATH, "out.json")
    assert os.path.exists(out_path)


@pytest.mark.buttons
def test_app_main(monkeypatch):
    """__main__ path can run without starting a real server."""
    monkeypatch.setattr(flask.Flask, "run", lambda *_, **__: None)
    runpy.run_module("app", run_name="__main__")
