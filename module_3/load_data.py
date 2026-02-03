import psycopg
from psycopg import OperationalError
import json
from pathlib import Path
from datetime import datetime


def create_connection(db_name, db_user, db_password, db_host, db_port):
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

def create_database(connection, query):
    connection.autocommit = True
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        print("Database created successfully")
    except OperationalError as e:
        print(f"The error '{e}' occurred")

def execute_query(connection, query):
    connection.autocommit = True
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        print("Query executed successfully")
    except OperationalError as e:
        print(f"The error '{e}' occurred")

def parse_date(s):
    if not s:
        return None
    return datetime.strptime(s, "%B %d, %Y").date()

def parse_float(s):
    if s is None or s =="":
        return None
    return float(s)

connection = create_connection("postgres", "postgres", "abc123", "127.0.0.1", "5432")

create_database(connection, "CREATE DATABASE sm_app")
connection.close()

connection = create_connection("sm_app", "postgres", "abc123", "127.0.0.1", "5432")


create_applicant_table = """
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
execute_query(connection, create_applicant_table)

insert_sql = """
INSERT INTO applicants (
program, university, comments, date_added, url, status, term, us_or_international, gpa, gre, gre_v, gre_aw, degree, llm_generated_program, llm_generated_university)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
"""

data_path = Path(__file__).with_name("out.json")
with open(data_path, "r") as f:
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
    cursor.execute(insert_sql, values)

connection.commit()
cursor.close()
