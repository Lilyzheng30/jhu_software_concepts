# Tests pipeline helpers and handler branches.
import os
import sys
import json
import runpy
import pytest

SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

import app as app_module


@pytest.mark.buttons
# test_run_pull_data_pipeline_busy()
def test_run_pull_data_pipeline_busy():
    app_module.is_pulling = True
    ok, status, seeded = app_module.run_pull_data_pipeline()
    assert ok is False
    assert "already running" in status
    assert seeded is False
    app_module.is_pulling = False


@pytest.mark.buttons
# test_run_pull_data_pipeline_exception(monkeypatch)
def test_run_pull_data_pipeline_exception(monkeypatch):
    def boom(*_, **__):
        raise Exception("fail")

    monkeypatch.setattr(app_module, "run_scrape", boom)
    app_module.is_pulling = False
    ok, status, _ = app_module.run_pull_data_pipeline()
    assert ok is False
    assert "Pull Data failed" in status


@pytest.mark.buttons
# test_handle_pull_data_redirects(monkeypatch)
def test_handle_pull_data_redirects(monkeypatch):
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
# test_pull_data_get_redirect()
def test_pull_data_get_redirect():
    client = app_module.app.test_client()
    resp = client.get("/pull-data")
    assert resp.status_code == 302


@pytest.mark.buttons
# test_pull_data_silent_success(monkeypatch)
def test_pull_data_silent_success(monkeypatch):
    monkeypatch.setattr(app_module, "run_pull_data_pipeline", lambda: (True, "ok", False))
    client = app_module.app.test_client()
    resp = client.post("/pull-data-silent")
    assert resp.status_code == 204


@pytest.mark.buttons
# test_pull_data_silent_busy(monkeypatch)
def test_pull_data_silent_busy(monkeypatch):
    monkeypatch.setattr(app_module, "run_pull_data_pipeline", lambda: (False, "busy", False))
    client = app_module.app.test_client()
    resp = client.post("/pull-data-silent")
    assert resp.status_code == 409


@pytest.mark.buttons
# test_update_analysis_get_redirect()
def test_update_analysis_get_redirect():
    client = app_module.app.test_client()
    resp = client.get("/update-analysis")
    assert resp.status_code == 302


@pytest.mark.buttons
# test_handle_update_analysis_busy()
def test_handle_update_analysis_busy():
    app_module.is_pulling = True
    with app_module.app.test_request_context("/update-analysis"):
        resp = app_module.handle_update_analysis()
        assert resp.status_code == 302
    app_module.is_pulling = False


@pytest.mark.buttons
# test_handle_update_analysis_not_busy()
def test_handle_update_analysis_not_busy():
    app_module.is_pulling = False
    with app_module.app.test_request_context("/update-analysis"):
        resp = app_module.handle_update_analysis()
        assert resp.status_code == 302


@pytest.mark.buttons
# test_pull_data_post_calls_handler(monkeypatch)
def test_pull_data_post_calls_handler(monkeypatch):
    monkeypatch.setattr(app_module, "handle_pull_data", lambda: ("ok", 302))
    client = app_module.app.test_client()
    resp = client.post("/pull-data")
    assert resp.status_code == 302


@pytest.mark.buttons
# test_update_analysis_post_calls_handler(monkeypatch)
def test_update_analysis_post_calls_handler(monkeypatch):
    monkeypatch.setattr(app_module, "handle_update_analysis", lambda: ("ok", 302))
    client = app_module.app.test_client()
    resp = client.post("/update-analysis")
    assert resp.status_code == 302


@pytest.mark.buttons
# test_run_llm_and_write_out_json(monkeypatch, tmp_path)
def test_run_llm_and_write_out_json(monkeypatch, tmp_path):
    # Ensure we run in src so relative paths resolve.
    monkeypatch.chdir(SRC_PATH)

    jsonl_path = os.path.join(SRC_PATH, "module_2", "llm_extend_applicant_data.json.jsonl")

    def fake_cli(*_, **__):
        with open(jsonl_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"url": "u1"}) + "\n")

    from module_2.llm_hosting import app as llm_app

    monkeypatch.setattr(llm_app, "_cli_process_file", fake_cli)
    app_module.run_llm_and_write_out_json()

    out_path = os.path.join(SRC_PATH, "out.json")
    assert os.path.exists(out_path)


@pytest.mark.buttons
# test_app_main(monkeypatch)
def test_app_main(monkeypatch):
    import flask

    monkeypatch.setattr(flask.Flask, "run", lambda *_, **__: None)
    runpy.run_module("app", run_name="__main__")
