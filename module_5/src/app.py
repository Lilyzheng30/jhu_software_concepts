"""Flask application for data pull and analytics dashboard routes."""

import json
import os
from contextlib import suppress

import psycopg
from psycopg import sql
from flask import Flask, jsonify, redirect, render_template, request, url_for

from db_config import read_database_url, read_db_params
from load_data import run_load
from query_data import QUERIES
from module_2.clean import run_clean
from module_2.llm_hosting import app as llm_app
from module_2.scrape import run_scrape


APP_STATE = {"is_pulling": False}
MIN_QUERY_LIMIT = 1
MAX_QUERY_LIMIT = 100
DEFAULT_QUERY_LIMIT = 25
ALLOWED_FILTER_COLUMNS = {
    "program": "program",
    "university": "university",
    "status": "status",
    "term": "term",
    "us_or_international": "us_or_international",
    "degree": "degree",
}
ALLOWED_SORT_COLUMNS = {
    "date_added": "date_added",
    "gpa": "gpa",
    "university": "university",
    "program": "program",
    "term": "term",
}
SELECTED_APPLICANT_COLUMNS = (
    "program",
    "university",
    "url",
    "status",
    "term",
    "us_or_international",
    "degree",
    "gpa",
)
# Backward-compatible alias used by existing tests.
globals()["is_pulling"] = False


def create_app():
    """Create and return the Flask app instance."""
    flask_app = Flask(__name__)
    return flask_app


app = create_app()


def _get_is_pulling():
    """Return pull-state, honoring legacy test assignments to is_pulling."""
    return APP_STATE["is_pulling"] or bool(globals().get("is_pulling", False))


def _set_is_pulling(value):
    """Set pull-state for both new and legacy state holders."""
    APP_STATE["is_pulling"] = bool(value)
    globals()["is_pulling"] = bool(value)


def get_db_connection():
    """Create DB connection from DB_* env vars, with DATABASE_URL fallback."""
    db_params = read_db_params("DB")
    if db_params:
        return psycopg.connect(**db_params)

    db_url = read_database_url()
    if db_url:
        return psycopg.connect(db_url)

    raise RuntimeError(
        "Database settings missing: set DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD "
        "or DATABASE_URL"
    )


def fetch_one_value(cursor, query):
    """Execute a scalar query and return the first value if available."""
    cursor.execute(query)
    row = cursor.fetchone()
    return row[0] if row else None


def fetch_existing_urls():
    """Read existing non-null URLs from the applicants table."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT url FROM applicants WHERE url IS NOT NULL;")
    urls = {row[0] for row in cur.fetchall() if row and row[0]}
    cur.close()
    conn.close()
    return urls


def clamp_limit(raw_limit, min_limit=MIN_QUERY_LIMIT, max_limit=MAX_QUERY_LIMIT):
    """Clamp user-provided limits to a safe bounded integer range."""
    try:
        parsed = int(raw_limit)
    except (TypeError, ValueError):
        parsed = DEFAULT_QUERY_LIMIT
    return max(min_limit, min(max_limit, parsed))


def build_safe_applicants_query(filters, sort_by, sort_direction, raw_limit):
    """Build a SQL-composed applicants query and its parameter list."""
    statement = sql.SQL("SELECT {cols} FROM {table}").format(
        cols=sql.SQL(", ").join([sql.Identifier(col) for col in SELECTED_APPLICANT_COLUMNS]),
        table=sql.Identifier("applicants"),
    )

    where_parts = []
    params = []
    for arg_name, column_name in ALLOWED_FILTER_COLUMNS.items():
        value = (filters.get(arg_name) or "").strip()
        if not value:
            continue
        where_parts.append(
            sql.SQL("{} ILIKE %s").format(sql.Identifier(column_name))
        )
        params.append(f"%{value}%")

    if where_parts:
        statement = sql.SQL("{} WHERE {}").format(
            statement,
            sql.SQL(" AND ").join(where_parts),
        )

    safe_sort_column = ALLOWED_SORT_COLUMNS.get(sort_by, "date_added")
    safe_direction = (
        sql.SQL("DESC")
        if str(sort_direction).strip().lower() == "desc"
        else sql.SQL("ASC")
    )
    statement = sql.SQL("{} ORDER BY {} {}").format(
        statement,
        sql.Identifier(safe_sort_column),
        safe_direction,
    )

    limited_value = clamp_limit(raw_limit)
    statement = sql.SQL("{} LIMIT %s").format(statement)
    params.append(limited_value)
    return statement, params, limited_value


def _rows_to_json(cursor_rows):
    """Map DB rows from applicants select into JSON-safe dictionaries."""
    out = []
    for row in cursor_rows:
        out.append(
            {
                "program": row[0],
                "university": row[1],
                "url": row[2],
                "status": row[3],
                "term": row[4],
                "us_or_international": row[5],
                "degree": row[6],
                "gpa": row[7],
            }
        )
    return out


def ensure_initial_dataset_loaded():
    """Seed the database from module_2_out.json when the applicants table is empty."""
    seeded = False
    conn = None
    with suppress(Exception):
        conn = get_db_connection()

    if conn is None:
        current_count = 0
    else:
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM applicants;")
            current_count = cur.fetchone()[0]
            cur.close()
            conn.close()
        except (psycopg.Error, RuntimeError):
            current_count = 0

    if current_count == 0:
        with suppress(Exception):
            run_load(input_file="module_2_out.json")
            seeded = True

    return seeded


def run_llm_and_write_out_json():
    """Run the LLM JSONL step and convert output to out.json."""
    input_path = "module_2/llm_extend_applicant_data.json"
    jsonl_path = "module_2/llm_extend_applicant_data.json.jsonl"
    out_json_path = "out.json"

    llm_app.cli_process_file(
        in_path=input_path,
        out_path=jsonl_path,
        append=False,
        to_stdout=False,
    )

    rows = []
    with open(jsonl_path, "r", encoding="utf-8") as file_in:
        for line in file_in:
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    with open(out_json_path, "w", encoding="utf-8") as file_out:
        json.dump(rows, file_out, indent=2, ensure_ascii=False)


def merge_out_into_module2_out():
    """Append only new URLs from out.json into module_2_out.json."""
    base_dir = os.path.dirname(__file__)
    master_path = os.path.join(base_dir, "module_2_out.json")
    batch_path = os.path.join(base_dir, "out.json")

    if os.path.exists(master_path):
        with open(master_path, "r", encoding="utf-8") as file_in:
            master_rows = json.load(file_in)
    else:
        master_rows = []

    with open(batch_path, "r", encoding="utf-8") as file_in:
        batch_rows = json.load(file_in)

    seen_urls = {
        (row.get("url") or "").strip()
        for row in master_rows
        if isinstance(row, dict) and row.get("url")
    }

    added = 0
    for row in batch_rows:
        if not isinstance(row, dict):
            continue
        url = (row.get("url") or "").strip()
        if not url or url in seen_urls:
            continue
        master_rows.append(row)
        seen_urls.add(url)
        added += 1

    with open(master_path, "w", encoding="utf-8") as file_out:
        json.dump(master_rows, file_out, indent=2, ensure_ascii=False)

    return added, len(master_rows)


@app.route("/")
@app.route("/analysis")
def home():
    """Render analysis page from current DB metrics."""
    seeded_now = ensure_initial_dataset_loaded()
    status_message = request.args.get("status")
    if seeded_now and not status_message:
        status_message = (
            "Database was empty, so initial data was loaded from module_2_out.json."
        )

    conn = get_db_connection()
    cur = conn.cursor()

    q1 = fetch_one_value(cur, QUERIES["q1"])
    q2 = fetch_one_value(cur, QUERIES["q2"])
    cur.execute(QUERIES["q3"])
    q3 = cur.fetchone()
    q4 = fetch_one_value(cur, QUERIES["q4"])
    q5 = fetch_one_value(cur, QUERIES["q5"])
    q6 = fetch_one_value(cur, QUERIES["q6"])
    q7 = fetch_one_value(cur, QUERIES["q7"])
    q8 = fetch_one_value(cur, QUERIES["q8"])
    q9 = fetch_one_value(cur, QUERIES["q9"])
    q10 = fetch_one_value(cur, QUERIES["q10"])
    q11 = fetch_one_value(cur, QUERIES["q11"])

    cur.close()
    conn.close()

    return render_template(
        "pages/home.html",
        q1=q1,
        q2=q2,
        q3_gpa=q3[0] if q3 else None,
        q3_gre=q3[1] if q3 else None,
        q3_gre_v=q3[2] if q3 else None,
        q3_gre_aw=q3[3] if q3 else None,
        q4=q4,
        q5=q5,
        q6=q6,
        q7=q7,
        q8=q8,
        q9=q9,
        q10=q10,
        q11=q11,
        status_message=status_message,
        is_pulling=_get_is_pulling(),
    )


def handle_pull_data():
    """Handle pull-data button route and redirect with status."""
    ok, status, seeded_now = run_pull_data_pipeline()
    if not ok:
        return redirect(url_for("home", status=status))

    if seeded_now:
        return redirect(
            url_for(
                "home",
                status=(
                    "Initial dataset loaded from module_2_out.json, then Pull Data "
                    "added newest rows."
                ),
            )
        )
    return redirect(url_for("home", status=status))


def run_pull_data_pipeline():
    """Run scrape -> clean -> LLM -> merge -> load DB pipeline."""
    if _get_is_pulling():
        return False, "Pull Data is already running. Please wait.", False

    _set_is_pulling(True)
    seeded_now = False
    try:
        seeded_now = ensure_initial_dataset_loaded()
        existing_urls = fetch_existing_urls()
        run_scrape(existing_urls=existing_urls, filename="module_2/applicant_data.json")
        run_clean(
            input_file="module_2/applicant_data.json",
            output_file="module_2/llm_extend_applicant_data.json",
        )
        run_llm_and_write_out_json()
        added_rows, total_rows = merge_out_into_module2_out()
        run_load(input_file="module_2_out.json")
        status = (
            f"Pull Data completed. Added {added_rows} new rows. "
            f"module_2_out now has {total_rows} rows."
        )
        return True, status, seeded_now
    except (RuntimeError, psycopg.Error, OSError, ValueError, json.JSONDecodeError) as err:
        return False, f"Pull Data failed: {err}", seeded_now
    finally:
        _set_is_pulling(False)


def handle_update_analysis():
    """Handle update-analysis button route and redirect with status."""
    if _get_is_pulling():
        return redirect(
            url_for("home", status="Update Analysis is unavailable while Pull Data is running.")
        )
    return redirect(url_for("home", status="Analysis updated with the latest available results."))


@app.route("/pull-data", methods=["GET", "POST"])
def pull_data():
    """Handle pull-data form endpoint."""
    if request.method == "GET":
        return redirect(url_for("home"))
    return handle_pull_data()


@app.route("/pull-data-silent", methods=["POST"])
def pull_data_silent():
    """Run pull pipeline without page navigation."""
    ok, status, _ = run_pull_data_pipeline()
    if not ok:
        return status, 409
    return "", 204


@app.route("/update-analysis", methods=["GET", "POST"])
def update_analysis():
    """Handle update-analysis endpoint."""
    if request.method == "GET":
        return redirect(url_for("home"))
    return handle_update_analysis()


@app.route("/api/pull-data", methods=["POST"])
def api_pull_data():
    """Run pull-data pipeline and return API JSON response."""
    ok, status, _ = run_pull_data_pipeline()
    if not ok:
        return jsonify({"ok": False, "error": status, "busy": _get_is_pulling()}), 409
    return jsonify({"ok": True, "status": status}), 200


@app.route("/api/update-analysis", methods=["POST"])
def api_update_analysis():
    """Check update-analysis availability for API clients."""
    if _get_is_pulling():
        return jsonify({"ok": False, "busy": True}), 409
    return jsonify({"ok": True}), 200


@app.route("/api/applicants", methods=["GET"])
def api_list_applicants():
    """List applicant rows using SQL-composed filtering, sorting, and safe limits."""
    filters = {
        "program": request.args.get("program", ""),
        "university": request.args.get("university", ""),
        "status": request.args.get("status", ""),
        "term": request.args.get("term", ""),
        "us_or_international": request.args.get("us_or_international", ""),
        "degree": request.args.get("degree", ""),
    }
    sort_by = request.args.get("sort_by", "date_added")
    sort_direction = request.args.get("sort_dir", "desc")
    raw_limit = request.args.get("limit", str(DEFAULT_QUERY_LIMIT))

    statement, params, safe_limit = build_safe_applicants_query(
        filters=filters,
        sort_by=sort_by,
        sort_direction=sort_direction,
        raw_limit=raw_limit,
    )

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(statement, params)
        rows = _rows_to_json(cur.fetchall())
    finally:
        cur.close()
        conn.close()

    return jsonify({"ok": True, "limit": safe_limit, "rows": rows}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
