import psycopg
import json
import os
from flask import Flask, render_template, request, redirect, url_for

from load_data import run_load
from module_2.clean import run_clean
from module_2.scrape import run_scrape
from query_data import QUERIES

def create_app():
    app = Flask(__name__)
    return app

app = create_app()
is_pulling = False


# Open a DB connection for app reads/writes
def get_db_connection():
    return psycopg.connect(
        dbname="sm_app",
        user="postgres",
        password="abc123",
        host="127.0.0.1",
        port="5432",
    )


# Run query and return first value
def fetch_one_value(cursor, query):
    cursor.execute(query)
    row = cursor.fetchone()
    return row[0] if row else None


# Read current URLs to avoid redoing existing entries
def fetch_existing_urls():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT url FROM applicants WHERE url IS NOT NULL;")
    urls = {row[0] for row in cur.fetchall() if row and row[0]}
    cur.close()
    conn.close()
    return urls


# initiates from module_2_out.json only when table is empty
def ensure_initial_dataset_loaded():
    seeded = False
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM applicants;")
        current_count = cur.fetchone()[0]
        cur.close()
        conn.close()
    except Exception:
        current_count = 0

    if current_count == 0:
        run_load(input_file="module_2_out.json")
        seeded = True

    return seeded


# Run local LLM step and convert jsonl output into out.json.
def run_llm_and_write_out_json():
    from module_2.llm_hosting.app import _cli_process_file

    input_path = "module_2/llm_extend_applicant_data.json"
    jsonl_path = "module_2/llm_extend_applicant_data.json.jsonl"
    out_json_path = "out.json"

    _cli_process_file(
        in_path=input_path,
        out_path=jsonl_path,
        append=False,
        to_stdout=False,
    )

    rows = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    with open(out_json_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)


# Merge newly generated out.json rows into cumulative module_2_out.json.
def merge_out_into_module2_out():
    """Append only new URLs from out.json into module_2_out.json."""
    base_dir = os.path.dirname(__file__)
    master_path = os.path.join(base_dir, "module_2_out.json")
    batch_path = os.path.join(base_dir, "out.json")

    if os.path.exists(master_path):
        with open(master_path, "r", encoding="utf-8") as f:
            master_rows = json.load(f)
    else:
        master_rows = []

    with open(batch_path, "r", encoding="utf-8") as f:
        batch_rows = json.load(f)

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

    with open(master_path, "w", encoding="utf-8") as f:
        json.dump(master_rows, f, indent=2, ensure_ascii=False)

    return added, len(master_rows)


@app.route("/")
# Render analysis page from current DB metrics.
def home():
    seeded_now = ensure_initial_dataset_loaded()
    status_message = request.args.get("status")
    if seeded_now and not status_message:
        status_message = "Database was empty, so initial data was loaded from module_2_out.json."
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
        is_pulling=is_pulling,
    )


# Web handler for Pull Data route 
def handle_pull_data():
    ok, status, seeded_now = run_pull_data_pipeline()
    if not ok:
        return redirect(url_for("home", status=status))

    if seeded_now:
        return redirect(
            url_for(
                "home",
                status="Initial dataset loaded from module_2_out.json, then Pull Data added newest rows.",
            )
        )
    return redirect(url_for("home", status=status))


# Full Pull Data pipeline: scrape -> clean -> LLM -> merge -> load DB
def run_pull_data_pipeline():
    global is_pulling
    if is_pulling:
        return False, "Pull Data is already running. Please wait.", False

    is_pulling = True
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
        # Load cumulative master dataset.
        run_load(input_file="module_2_out.json")
        status = (
            f"Pull Data completed. Added {added_rows} new rows. "
            f"module_2_out now has {total_rows} rows."
        )
        return True, status, seeded_now
    except Exception as e:
        return False, f"Pull Data failed: {e}", seeded_now
    finally:
        is_pulling = False

# Web handler for Update Analysis action
def handle_update_analysis():
    if is_pulling:
        return redirect(
            url_for("home", status="Update Analysis is unavailable while Pull Data is running.")
        )
    return redirect(url_for("home", status="Analysis updated with the latest available results."))


@app.route("/pull-data", methods=["GET", "POST"])
# Standard pull-data endpoint used by form submits
def pull_data():
    if request.method == "GET":
        return redirect(url_for("home"))
    return handle_pull_data()


@app.route("/pull-data-silent", methods=["POST"])
# Silent endpoint: run pull pipeline without page navigation
def pull_data_silent():
    ok, status, _ = run_pull_data_pipeline()
    if not ok:
        return status, 409
    return "", 204


@app.route("/update-analysis", methods=["GET", "POST"])
# Update-analysis endpoint
def update_analysis():
    if request.method == "GET":
        return redirect(url_for("home"))
    return handle_update_analysis()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug = True)
