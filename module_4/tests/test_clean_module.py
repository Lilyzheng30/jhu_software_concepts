import os
import sys
import json
import pytest

SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

from module_2.clean import clean_data, load_data, save_data, run_clean


@pytest.mark.db
def test_clean_data_basic_fields():
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
    cleaned = clean_data(raw)
    assert cleaned[0]["program"] == "Computer Science"
    assert cleaned[0]["university"] == "Johns Hopkins University"
    assert cleaned[0]["citizenship"] == "International"
    assert cleaned[0]["gpa"] == "3.9"
    assert cleaned[0]["applicant_status"].startswith("Accepted on")
    assert cleaned[0]["acceptance_date"] == "Jan 01, 2025"


@pytest.mark.db
def test_clean_data_normalizes_zero_values():
    raw = [
        {
            "gre_score_raw": "0",
            "gre_v_score_raw": "0.0",
            "gre_aw_raw": "0.00",
            "gpa_raw": "0",
        }
    ]
    cleaned = clean_data(raw)
    assert cleaned[0]["gre_total"] is None
    assert cleaned[0]["gre_verbal"] is None
    assert cleaned[0]["gre_writing"] is None
    assert cleaned[0]["gpa"] is None


@pytest.mark.db
def test_clean_data_rejected_branch():
    raw = [{"applicant_status_raw": "Rejected on Feb 02, 2025"}]
    cleaned = clean_data(raw)
    assert cleaned[0]["rejection_date"] == "Feb 02, 2025"


@pytest.mark.db
def test_load_save_and_run_clean(tmp_path):
    inp = tmp_path / "in.json"
    outp = tmp_path / "out.json"
    data = [{"program_raw": "Math", "url": "u1"}]
    inp.write_text(json.dumps(data))

    loaded = load_data(str(inp))
    assert loaded == data

    save_data([{"program": "Math"}], str(outp))
    assert json.loads(outp.read_text())[0]["program"] == "Math"

    result = run_clean(input_file=str(inp), output_file=str(outp))
    assert result[0]["program"] == "Math"


@pytest.mark.db
def test_run_clean_main(monkeypatch, tmp_path):
    import runpy

    inp = tmp_path / "applicant_data.json"
    inp.write_text(json.dumps([{"program_raw": "Math", "url": "u1"}]))
    monkeypatch.chdir(tmp_path)
    runpy.run_module("module_2.clean", run_name="__main__")
