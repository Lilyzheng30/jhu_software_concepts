"""Shared environment-variable readers for DB connection settings."""

import os


def read_db_params(prefix="DB"):
    """Return psycopg kwargs dict from <prefix>_* env vars, or None."""
    db_host = os.getenv(f"{prefix}_HOST")
    db_port = os.getenv(f"{prefix}_PORT")
    db_name = os.getenv(f"{prefix}_NAME")
    db_user = os.getenv(f"{prefix}_USER")
    db_password = os.getenv(f"{prefix}_PASSWORD")
    if not all([db_host, db_port, db_name, db_user]):
        return None

    params = {
        "host": db_host,
        "port": db_port,
        "dbname": db_name,
        "user": db_user,
    }
    if db_password:
        params["password"] = db_password
    return params


def read_database_url():
    """Return DATABASE_URL value if set, otherwise None."""
    return os.getenv("DATABASE_URL")
