"""Tests cleaning helpers and module_2.clean entrypoint."""

import importlib
import json
import os
import runpy
import sys

import pytest

SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

clean_mod = importlib.import_module("module_2.clean")


@pytest.mark.db
def test_clean_data_basic_fields():
    """Basic clean_data mapping populates normalized output fields."""
    raw = [
        {
            "program_raw": " Computer Science ",
            "university_raw": " Johns Hopkins University ",
            "comments_raw": " test ",
            "date_added_raw": "2025-01-01",
            "semester_year_start_raw": "Fall 2026",
            "international_american_raw": "International",
            "gre_score_raw": "330",
            "gre_v_score_raw": "165",
            "gre_aw_raw": "4.5",
            "degree_type_raw": "Masters",
            "gpa_raw": "3.9",
            "url": "https://example.com/a",
            "applicant_status_raw": "Accepted on Jan 01, 2025",
        }
    ]
    cleaned = clean_mod.clean_data(raw)
    assert cleaned[0]["program"] == "Computer Science"
    assert cleaned[0]["university"] == "Johns Hopkins University"
    assert cleaned[0]["citizenship"] == "International"
    assert cleaned[0]["gpa"] == "3.9"
    assert cleaned[0]["applicant_status"].startswith("Accepted on")
    assert cleaned[0]["acceptance_date"] == "Jan 01, 2025"


@pytest.mark.db
def test_clean_data_normalizes_zero_values():
    """Zero-like GRE/GPA strings are converted to None."""
    raw = [{"gre_score_raw": "0", "gre_v_score_raw": "0.0", "gre_aw_raw": "0.00", "gpa_raw": "0"}]
    cleaned = clean_mod.clean_data(raw)
    assert cleaned[0]["gre_total"] is None
    assert cleaned[0]["gre_verbal"] is None
    assert cleaned[0]["gre_writing"] is None
    assert cleaned[0]["gpa"] is None


@pytest.mark.db
def test_clean_data_rejected_branch():
    """Rejected status branch populates rejection_date."""
    cleaned = clean_mod.clean_data([{"applicant_status_raw": "Rejected on Feb 02, 2025"}])
    assert cleaned[0]["rejection_date"] == "Feb 02, 2025"


@pytest.mark.db
def test_load_save_and_run_clean(tmp_path):
    """load_data, save_data, and run_clean work with temporary files."""
    inp = tmp_path / "in.json"
    outp = tmp_path / "out.json"
    data = [{"program_raw": "Math", "url": "u1"}]
    inp.write_text(json.dumps(data))

    loaded = clean_mod.load_data(str(inp))
    assert loaded == data

    clean_mod.save_data([{"program": "Math"}], str(outp))
    assert json.loads(outp.read_text())[0]["program"] == "Math"

    result = clean_mod.run_clean(input_file=str(inp), output_file=str(outp))
    assert result[0]["program"] == "Math"


@pytest.mark.db
def test_run_clean_main(monkeypatch, tmp_path):
    """module_2.clean __main__ path runs without crashing."""
    inp = tmp_path / "applicant_data.json"
    inp.write_text(json.dumps([{"program_raw": "Math", "url": "u1"}]))

    monkeypatch.chdir(tmp_path)
    runpy.run_module("module_2.clean", run_name="__main__")
