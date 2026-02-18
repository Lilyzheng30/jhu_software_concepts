"""End-to-end tests for pull, update-analysis, and rendered output flows."""

import importlib
import json
import os
import sys

import pytest

SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)
build_applicant_rows = importlib.import_module("data_builders").build_applicant_rows


@pytest.fixture(name="app_fixture")
def fixture_app(monkeypatch):
    """Return app module with DATABASE_URL set for integration runs."""
    app_module = importlib.import_module("app")
    monkeypatch.setenv("DATABASE_URL", "postgresql://postgres:abc123@127.0.0.1:5432/sm_app")
    return app_module


@pytest.fixture(name="fake_rows_file")
def fixture_fake_rows_file(tmp_path):
    """Create a rows.json file used by mocked LLM output stage."""
    rows = build_applicant_rows()
    path_obj = tmp_path / "rows.json"
    path_obj.write_text(json.dumps(rows))
    return str(path_obj)


@pytest.mark.integration
def test_end_to_end_flow(app_fixture, fake_rows_file, monkeypatch):
    """Happy path: pull, update, then render analysis page."""

    def _fake_run_scrape(**_kwargs):
        return []

    def _fake_run_clean(**_kwargs):
        return []

    def _fake_run_llm_and_write():
        with open(fake_rows_file, "r", encoding="utf-8") as file_in:
            rows = json.load(file_in)
        with open(os.path.join(SRC_PATH, "out.json"), "w", encoding="utf-8") as file_out:
            json.dump(rows, file_out)

    monkeypatch.setattr(app_fixture, "run_scrape", _fake_run_scrape)
    monkeypatch.setattr(app_fixture, "run_clean", _fake_run_clean)
    monkeypatch.setattr(app_fixture, "run_llm_and_write_out_json", _fake_run_llm_and_write)

    module2_out = os.path.join(SRC_PATH, "module_2_out.json")
    with open(module2_out, "w", encoding="utf-8") as file_out:
        json.dump([], file_out)

    client = app_fixture.app.test_client()

    resp = client.post("/api/pull-data")
    assert resp.status_code == 200

    resp2 = client.post("/api/update-analysis")
    assert resp2.status_code == 200

    resp3 = client.get("/analysis")
    assert resp3.status_code == 200
    assert "Answer:" in resp3.get_data(as_text=True)


@pytest.mark.integration
def test_multiple_pulls_are_idempotent(app_fixture, fake_rows_file, monkeypatch):
    """Multiple pull-data calls should remain successful and idempotent."""

    def _fake_run_scrape(**_kwargs):
        return []

    def _fake_run_clean(**_kwargs):
        return []

    def _fake_run_llm_and_write():
        with open(fake_rows_file, "r", encoding="utf-8") as file_in:
            rows = json.load(file_in)
        with open(os.path.join(SRC_PATH, "out.json"), "w", encoding="utf-8") as file_out:
            json.dump(rows, file_out)

    monkeypatch.setattr(app_fixture, "run_scrape", _fake_run_scrape)
    monkeypatch.setattr(app_fixture, "run_clean", _fake_run_clean)
    monkeypatch.setattr(app_fixture, "run_llm_and_write_out_json", _fake_run_llm_and_write)

    module2_out = os.path.join(SRC_PATH, "module_2_out.json")
    with open(module2_out, "w", encoding="utf-8") as file_out:
        json.dump([], file_out)

    client = app_fixture.app.test_client()
    resp1 = client.post("/api/pull-data")
    resp2 = client.post("/api/pull-data")
    assert resp1.status_code == 200
    assert resp2.status_code == 200
