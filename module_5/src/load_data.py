"""Load cleaned JSON records into PostgreSQL."""

import json
import os
from datetime import datetime
from pathlib import Path

import psycopg
from psycopg import OperationalError
from psycopg import sql
from db_config import read_database_url, read_db_params


def create_connection(db_name, db_user, db_password, db_host, db_port):
    """Create a PostgreSQL connection with provided credentials."""
    try:
        params = {
            "dbname": db_name,
            "user": db_user,
            "host": db_host,
            "port": db_port,
        }
        if db_password is not None:
            params["password"] = db_password
        return psycopg.connect(**params)
    except OperationalError as e:
        print(f"The error '{e}' occurred")
        return None


def create_connection_from_env():
    """Create app DB connection from DB_* vars, with DATABASE_URL fallback."""
    db_params = read_db_params("DB")
    if db_params:
        return create_connection(
            db_params["dbname"],
            db_params["user"],
            db_params.get("password"),
            db_params["host"],
            db_params["port"],
        )

    db_url = read_database_url()
    if db_url:
        try:
            return psycopg.connect(conninfo=db_url)
        except OperationalError as e:
            print(f"The error '{e}' occurred")
            return None
    try:
        return psycopg.connect()
    except OperationalError as e:
        print(f"The error '{e}' occurred")
        return None


def create_admin_connection_from_env():
    """Create admin DB connection for optional DB creation/bootstrap."""
    admin_params = read_db_params("DB_ADMIN")
    if admin_params:
        return create_connection(
            admin_params["dbname"],
            admin_params["user"],
            admin_params.get("password"),
            admin_params["host"],
            admin_params["port"],
        )
    return None


def create_database(connection, query):
    """Execute a database-level SQL command."""
    connection.autocommit = True
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        print("Database created successfully")
    except psycopg.Error as e:
        print(f"The error '{e}' occurred")

def execute_query(connection, query):
    """Execute a SQL statement on an open connection."""
    connection.autocommit = True
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        print("Query executed successfully")
    except OperationalError as e:
        print(f"The error '{e}' occurred")

def parse_date(s):
    """Parse known date string formats into date objects."""
    if not s:
        return None
    if isinstance(s, str):
        s = s.strip()
    for fmt in ("%B %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except (TypeError, ValueError):
            continue
    return None

def parse_float(s):
    """Convert numeric text to float while preserving empty values as NULL."""
    if s is None or s == "":
        return None
    return float(s)

# applicants table and setting the columns
CREATE_APPLICANT_TABLE = """
CREATE TABLE IF NOT EXISTS applicants (
  p_id SERIAL PRIMARY KEY,
  program TEXT,
  university TEXT,
  comments TEXT,
  date_added DATE,
  url TEXT,
  status TEXT,
  term TEXT,
  us_or_international TEXT,
  gpa FLOAT,
  gre FLOAT,
  gre_v FLOAT,
  gre_aw FLOAT,
  degree TEXT,
  llm_generated_program TEXT,
  llm_generated_university TEXT
);
"""

CREATE_URL_UNIQUE_INDEX = """
CREATE UNIQUE INDEX IF NOT EXISTS applicants_url_unique_idx
ON applicants (url);
"""

# Keep only one row per URL if there is duplicate (oldest p_id wins)
DEDUPE_EXISTING_URLS = """
DELETE FROM applicants a
USING applicants b
WHERE a.url IS NOT NULL
  AND b.url IS NOT NULL
  AND a.url = b.url
  AND a.p_id > b.p_id;
"""

INSERT_SQL = """
INSERT INTO applicants (
program, university, comments, date_added, url, status, term, us_or_international, gpa, gre, gre_v, gre_aw, degree, llm_generated_program, llm_generated_university)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (url) DO NOTHING;
"""

def run_load(input_file="module_2_out.json"):
    """Load JSON rows into PostgreSQL, creating DB/table/index as needed."""
    app_db_name = os.getenv("DB_NAME")
    if not app_db_name:
        db_url = os.getenv("DATABASE_URL", "")
        if "/" in db_url:
            app_db_name = db_url.rsplit("/", maxsplit=1)[-1].split("?", maxsplit=1)[0]

    admin_connection = create_admin_connection_from_env()
    if admin_connection is not None and app_db_name:
        create_database(
            admin_connection,
            sql.SQL("CREATE DATABASE {}").format(sql.Identifier(app_db_name)),
        )
        admin_connection.close()

    connection = create_connection_from_env()
    if connection is None:
        raise RuntimeError(
            "Failed DB connection. Set DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD "
            "or DATABASE_URL."
        )
    execute_query(connection, CREATE_APPLICANT_TABLE)
    # Remove existing duplicate URLs before creating unique index
    execute_query(connection, DEDUPE_EXISTING_URLS)
    execute_query(connection, CREATE_URL_UNIQUE_INDEX)

    data_path = Path(input_file)
    if not data_path.is_absolute():
        data_path = Path(__file__).with_name(input_file)

    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    cursor = connection.cursor()
    for rec in data:
        values = (
            rec.get("program"),
            rec.get("university"),
            rec.get("comments"),
            parse_date(rec.get("date_added")),
            rec.get("url"),
            rec.get("applicant_status"),
            rec.get("semester_year_start"),
            rec.get("citizenship"),
            parse_float(rec.get("gpa")),
            parse_float(rec.get("gre_total")),
            parse_float(rec.get("gre_verbal")),
            parse_float(rec.get("gre_writing")),
            rec.get("degree_type"),
            rec.get("llm-generated-program"),
            rec.get("llm-generated-university"),
        )
        cursor.execute(INSERT_SQL, values)

    connection.commit()
    cursor.close()
    connection.close()


if __name__ == "__main__":
    run_load()
