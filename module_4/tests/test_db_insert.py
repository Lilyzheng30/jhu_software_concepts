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
def temp_json(tmp_path):
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
            "university": "Johns Hopkins University",
            "comments": "Duplicate",
            "date_added": "2025-01-02",
            "url": "https://example.com/a",
            "applicant_status": "Accepted on Jan 02, 2025",
            "semester_year_start": "Fall 2026",
            "citizenship": "International",
            "gpa": "3.8",
            "gre_total": "329",
            "gre_verbal": "164",
            "gre_writing": "4.0",
            "degree_type": "Masters",
            "llm-generated-program": "Computer Science",
            "llm-generated-university": "Johns Hopkins University",
        },
    ]
    p = tmp_path / "rows.json"
    p.write_text(json.dumps(rows))
    return str(p)


@pytest.mark.db
def test_insert_and_idempotency(temp_json):
    from load_data import run_load
    import psycopg

    run_load(input_file=temp_json)

    conn = psycopg.connect(
        dbname="sm_app",
        user="postgres",
        password="abc123",
        host="127.0.0.1",
        port="5432",
    )
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM applicants WHERE url = 'https://example.com/a';")
    count = cur.fetchone()[0]
    assert count == 1

    cur.execute(
        "SELECT program, university, url, status, term, us_or_international FROM applicants WHERE url = 'https://example.com/a';"
    )
    row = cur.fetchone()
    assert row[0] is not None
    assert row[1] is not None
    assert row[2] is not None
    assert row[3] is not None
    assert row[4] is not None
    assert row[5] is not None

    cur.close()
    conn.close()


@pytest.mark.db
def test_simple_query_returns_expected_keys():
    import psycopg

    conn = psycopg.connect(
        dbname="sm_app",
        user="postgres",
        password="abc123",
        host="127.0.0.1",
        port="5432",
    )
    cur = conn.cursor()
    cur.execute(
        "SELECT program, university, url, status, term, us_or_international FROM applicants LIMIT 1;"
    )
    row = cur.fetchone()
    assert row is not None
    keys = ["program", "university", "url", "status", "term", "us_or_international"]
    data = dict(zip(keys, row))
    assert set(keys).issubset(data.keys())

    cur.close()
    conn.close()
