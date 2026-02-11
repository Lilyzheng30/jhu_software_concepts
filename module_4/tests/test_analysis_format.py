import os
import sys
import pytest

SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)


class _FormatCursor:
    def __init__(self):
        self.calls = 0

    def execute(self, query):
        self.calls += 1

    def fetchone(self):
        # Third query is q3 (tuple of 4 values)
        if self.calls == 3:
            return (3.45, 320.12, 160.34, 4.56)
        # All other single values (ensure percentages show 2 decimals)
        if self.calls == 2:  # q2
            return (12.34,)
        if self.calls == 5:  # q5
            return (56.78,)
        return (1,)

    def close(self):
        return None


class _FormatConn:
    def cursor(self):
        return _FormatCursor()

    def close(self):
        return None


@pytest.fixture
def app_module(monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "get_db_connection", lambda: _FormatConn())
    monkeypatch.setattr(app_module, "ensure_initial_dataset_loaded", lambda: False)
    return app_module


@pytest.mark.analysis
def test_labels_and_percentage_format(app_module):
    client = app_module.app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    text = resp.get_data(as_text=True)

    assert "Answer:" in text
    assert "12.34%" in text
    assert "56.78%" in text
