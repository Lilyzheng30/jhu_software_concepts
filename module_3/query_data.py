import psycopg
from psycopg import OperationalError


QUERIES = {
    "q1": """
        SELECT COUNT(*)
        FROM applicants
        WHERE term = 'Fall 2026';
    """,
    "q2": """
        SELECT ROUND(
            100.0 * SUM(CASE WHEN us_or_international NOT IN ('American', 'Other') THEN 1 ELSE 0 END) / COUNT(*),
            2
        )
        FROM applicants;
    """,
    "q3": """
        SELECT
            ROUND(AVG(gpa)::numeric, 2),
            ROUND(AVG(gre)::numeric, 2),
            ROUND(AVG(gre_v)::numeric, 2),
            ROUND(AVG(gre_aw)::numeric, 2)
        FROM applicants;
    """,
    "q4": """
        SELECT ROUND(AVG(gpa)::numeric, 2)
        FROM applicants
        WHERE us_or_international = 'American' AND term = 'Fall 2026';
    """,
    "q5": """
        SELECT ROUND(
            100.0 * SUM(CASE WHEN status ILIKE 'Accepted on%' THEN 1 ELSE 0 END) / COUNT(*),
            2
        )
        FROM applicants
        WHERE term = 'Fall 2026';
    """,
    "q6": """
        SELECT ROUND(AVG(gpa)::numeric, 2)
        FROM applicants
        WHERE term = 'Fall 2026' AND status ILIKE 'Accepted on%';
    """,
    "q7": """
        SELECT COUNT(*)
        FROM applicants
        WHERE degree = 'Masters' AND program = 'Computer Science' AND university = 'Johns Hopkins University';
    """,
    "q8": """
        SELECT COUNT(*)
        FROM applicants
        WHERE term ILIKE '%2026%'
        AND (
            university ILIKE 'Georgetown University'
            OR university ILIKE '%Massachusetts Institute of Technology%'
            OR university ILIKE 'Stanford%'
            OR university ILIKE 'Carnegie Mellon University'
            )          
        AND degree = 'PhD'
        AND program ILIKE '%Computer Science%'
        AND status ILIKE 'Accepted on%';
    """,
    "q9": """
        SELECT COUNT(*)
        FROM applicants
        WHERE term ILIKE '%2026%'
          AND (
            llm_generated_university ILIKE 'Georgetown University'
            OR llm_generated_university ILIKE '%Massachusetts Institute of Technology%'
            OR llm_generated_university ILIKE 'Stanford%'
            OR llm_generated_university ILIKE 'Carnegie Mellon University'
            )
          AND degree = 'PhD'
          AND llm_generated_program ILIKE '%Computer Science%'
          AND status ILIKE 'Accepted on%';
    """,
    "q10": """
        SELECT COUNT(*)
        FROM applicants
        WHERE university = 'Johns Hopkins University'
          AND status ILIKE 'Accepted on%'
          AND us_or_international NOT IN ('American', 'Other');
    """,
    "q11": """
        SELECT ROUND(AVG(gpa)::numeric, 2)
        FROM applicants
        WHERE university = 'Harvard University'
          AND program = 'Computer Science'
          AND status ILIKE 'Accepted on%';
    """,
}


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


def execute_read_query(connection, query):
    connection.autocommit = True
    cursor = connection.cursor()
    result = None
    try:
        cursor.execute(query)
        result = cursor.fetchall()
        return result
    except OperationalError as e:
        print(f"The error '{e}' occurred")


if __name__ == "__main__":
    connection = create_connection("sm_app", "postgres", "abc123", "127.0.0.1", "5432")

    def first_value(query):
        rows = execute_read_query(connection, query)
        if not rows:
            return None
        return rows[0][0]

    applicant_count = first_value(QUERIES["q1"])
    international_count = first_value(
        "SELECT COUNT(*) FROM applicants WHERE us_or_international NOT IN ('American', 'Other');"
    )
    us_count = first_value(
        "SELECT COUNT(*) FROM applicants WHERE us_or_international = 'American';"
    )
    other_count = first_value(
        "SELECT COUNT(*) FROM applicants WHERE us_or_international = 'Other';"
    )
    percent_international = first_value(QUERIES["q2"])

    q3_rows = execute_read_query(connection, QUERIES["q3"])
    q3 = q3_rows[0] if q3_rows else (None, None, None, None)

    avg_gpa_american = first_value(QUERIES["q4"])
    acceptance_percent = first_value(QUERIES["q5"])
    acceptance_count = first_value(
        "SELECT COUNT(*) FROM applicants WHERE term = 'Fall 2026' AND status ILIKE 'Accepted on%';"
    )
    avg_gpa_acceptance = first_value(QUERIES["q6"])
    jhu_masters_cs_count = first_value(QUERIES["q7"])

    print(f"Applicant count: {applicant_count}")
    print(f"International count: {international_count}")
    print(f"US count: {us_count}")
    print(f"Other count: {other_count}")
    print(f"Percent International: {percent_international}")
    print(
        f"Average GPA: {q3[0]}, Average GRE: {q3[1]}, "
        f"Average GRE V: {q3[2]}, Average GRE AW: {q3[3]}"
    )
    print(f"Average GPA American: {avg_gpa_american}")
    print(f"Acceptance count: {acceptance_count}")
    print(f"Acceptance percent: {acceptance_percent}")
    print(f"Average GPA Acceptance: {avg_gpa_acceptance}")
    print(f"JHU Masters Computer Science count: {jhu_masters_cs_count}")

    connection.close()
