"""Tests DB insert idempotency and row-shape query checks."""

import importlib
import json
import os
import sys

import pytest

SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)
build_applicant_rows = importlib.import_module("data_builders").build_applicant_rows

app_fixture_module = importlib.import_module("app")


@pytest.fixture
def app_fixture():
    """Return imported app module used by integration tests."""
    return app_fixture_module


@pytest.fixture(name="temp_json")
def fixture_temp_json(tmp_path):
    """Write a temp JSON file with duplicate URL rows."""
    rows = build_applicant_rows()
    rows[1]["url"] = rows[0]["url"]
    rows[1]["comments"] = "Duplicate"
    rows[1]["university"] = rows[0]["university"]
    path_obj = tmp_path / "rows.json"
    path_obj.write_text(json.dumps(rows))
    return str(path_obj)


@pytest.mark.db
def test_insert_and_idempotency(temp_json):
    """run_load inserts one row per URL despite duplicates in JSON."""
    run_load = importlib.import_module("load_data").run_load
    psycopg = importlib.import_module("psycopg")

    run_load(input_file=temp_json)

    db_url = os.getenv("DATABASE_URL")
    assert db_url is not None

    conn = psycopg.connect(db_url)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM applicants WHERE url = 'https://example.com/a';")
    count = cur.fetchone()[0]
    assert count == 1

    cur.execute(
        "SELECT program, university, url, status, term, us_or_international "
        "FROM applicants WHERE url = 'https://example.com/a';"
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
    """Simple SELECT query returns values mappable to expected keys."""
    psycopg = importlib.import_module("psycopg")

    db_url = os.getenv("DATABASE_URL")
    assert db_url is not None

    conn = psycopg.connect(db_url)
    cur = conn.cursor()
    cur.execute(
        "SELECT program, university, url, status, term, us_or_international "
        "FROM applicants LIMIT 1;"
    )
    row = cur.fetchone()
    assert row is not None

    keys = ["program", "university", "url", "status", "term", "us_or_international"]
    data = dict(zip(keys, row))
    assert set(keys).issubset(data.keys())

    cur.close()
    conn.close()
