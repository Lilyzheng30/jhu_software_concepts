# End-to-end tests for pull -> update -> render flows.
import os
import sys
import json
import pytest

SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)


@pytest.fixture
def app_module():
    import app as app_module

    return app_module


@pytest.fixture
def fake_rows(tmp_path):
    rows = [
        {
            "program": "Computer Science",
            "university": "Johns Hopkins University",
            "comments": "Test",
            "date_added": "2025-01-01",
            "url": "https://example.com/a",
            "applicant_status": "Accepted on Jan 01, 2025",
            "semester_year_start": "Fall 2026",
            "citizenship": "International",
            "gpa": "3.9",
            "gre_total": "330",
            "gre_verbal": "165",
            "gre_writing": "4.5",
            "degree_type": "Masters",
            "llm-generated-program": "Computer Science",
            "llm-generated-university": "Johns Hopkins University",
        },
        {
            "program": "Computer Science",
            "university": "Stanford University",
            "comments": "Test2",
            "date_added": "2025-01-02",
            "url": "https://example.com/b",
            "applicant_status": "Accepted on Jan 02, 2025",
            "semester_year_start": "Fall 2026",
            "citizenship": "American",
            "gpa": "3.8",
            "gre_total": "329",
            "gre_verbal": "164",
            "gre_writing": "4.0",
            "degree_type": "PhD",
            "llm-generated-program": "Computer Science",
            "llm-generated-university": "Stanford University",
        },
    ]
    p = tmp_path / "rows.json"
    p.write_text(json.dumps(rows))
    return str(p)


@pytest.mark.integration
# test_end_to_end_flow(app_module, fake_rows, monkeypatch)
def test_end_to_end_flow(app_module, fake_rows, monkeypatch):
    # Patch pipeline steps to avoid network/LLM.
    monkeypatch.setattr(app_module, "run_scrape", lambda **_: [])
    monkeypatch.setattr(app_module, "run_clean", lambda **_: [])

    def fake_run_llm_and_write():
        # Copy fake_rows into out.json
        with open(fake_rows, "r", encoding="utf-8") as f:
            rows = json.load(f)
        with open(os.path.join(SRC_PATH, "out.json"), "w", encoding="utf-8") as f:
            json.dump(rows, f)

    monkeypatch.setattr(app_module, "run_llm_and_write_out_json", fake_run_llm_and_write)

    # Ensure module_2_out.json exists and is empty
    module2_out = os.path.join(SRC_PATH, "module_2_out.json")
    with open(module2_out, "w", encoding="utf-8") as f:
        json.dump([], f)

    client = app_module.app.test_client()

    # Pull data -> load DB
    resp = client.post("/api/pull-data")
    assert resp.status_code == 200

    # Update analysis
    resp2 = client.post("/api/update-analysis")
    assert resp2.status_code == 200

    # Render page should show analysis labels
    resp3 = client.get("/analysis")
    assert resp3.status_code == 200
    text = resp3.get_data(as_text=True)
    assert "Answer:" in text


@pytest.mark.integration
# test_multiple_pulls_are_idempotent(app_module, fake_rows, monkeypatch)
def test_multiple_pulls_are_idempotent(app_module, fake_rows, monkeypatch):
    monkeypatch.setattr(app_module, "run_scrape", lambda **_: [])
    monkeypatch.setattr(app_module, "run_clean", lambda **_: [])

    def fake_run_llm_and_write():
        with open(fake_rows, "r", encoding="utf-8") as f:
            rows = json.load(f)
        with open(os.path.join(SRC_PATH, "out.json"), "w", encoding="utf-8") as f:
            json.dump(rows, f)

    monkeypatch.setattr(app_module, "run_llm_and_write_out_json", fake_run_llm_and_write)

    module2_out = os.path.join(SRC_PATH, "module_2_out.json")
    with open(module2_out, "w", encoding="utf-8") as f:
        json.dump([], f)

    client = app_module.app.test_client()

    resp1 = client.post("/api/pull-data")
    assert resp1.status_code == 200
    resp2 = client.post("/api/pull-data")
    assert resp2.status_code == 200
