import psycopg
from flask import Flask, render_template

from query_data import QUERIES

app = Flask(__name__)


def get_db_connection():
    return psycopg.connect(
        dbname="sm_app",
        user="postgres",
        password="abc123",
        host="127.0.0.1",
        port="5432",
    )


def fetch_one_value(cursor, query):
    cursor.execute(query)
    row = cursor.fetchone()
    return row[0] if row else None


@app.route("/")
def home():
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
    )


@app.route("/create/")
def create():
    return render_template("pages/create.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
