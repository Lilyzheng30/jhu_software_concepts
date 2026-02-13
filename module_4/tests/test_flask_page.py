import os
import sys
import pytest

SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)


class FakeCursor:
    def __init__(self):
        self.queries = []
        self.fetchone_values = [
            (0,),  # q1
            (0.0,),  # q2
            (0.0,),  # q4
            (0.0,),  # q5
            (0.0,),  # q6
            (0,),  # q7
            (0,),  # q8
            (0,),  # q9
            (0,),  # q10
            (0.0,),  # q11
        ]
        self.q3_row = (0.0, 0.0, 0.0, 0.0)

    def execute(self, query):
        self.queries.append(query)

    def fetchone(self):
        if "AVG(gpa)::numeric" in self.queries[-1]:
            return self.q3_row
        if self.fetchone_values:
            return self.fetchone_values.pop(0)
        return None

    def close(self):
        return None


class FakeConnection:
    def __init__(self):
        self.cursor_obj = FakeCursor()

    def cursor(self):
        return self.cursor_obj

    def close(self):
        return None


@pytest.fixture
def app_module(monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "get_db_connection", lambda: FakeConnection())
    monkeypatch.setattr(app_module, "ensure_initial_dataset_loaded", lambda: False)
    return app_module


@pytest.mark.web
def test_routes_exist(app_module):
    routes = {rule.rule for rule in app_module.app.url_map.iter_rules()}
    assert "/" in routes
    assert "/pull-data" in routes
    assert "/pull-data-silent" in routes
    assert "/update-analysis" in routes


@pytest.mark.web
def test_create_app(app_module):
    from flask import Flask

    app = app_module.create_app()
    assert app is not None
    assert isinstance(app, Flask)


@pytest.mark.web
def test_get_home_page_renders(app_module):
    client = app_module.app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    assert "Pull Data" in text
    assert "Update Analysis" in text
    assert "Analysis" in text
    assert "Answer:" in text
