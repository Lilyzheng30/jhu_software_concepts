# Tests pull/update endpoints and busy-state behavior.
import os
import sys
import pytest

SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)


@pytest.fixture
def app_module():
    import app as app_module

    return app_module


@pytest.mark.buttons
# test_post_pull_data_triggers_pipeline(app_module, monkeypatch)
def test_post_pull_data_triggers_pipeline(app_module, monkeypatch):
    called = {"ok": False}

    def fake_run_pull():
        called["ok"] = True
        return True, "ok", False

    monkeypatch.setattr(app_module, "run_pull_data_pipeline", fake_run_pull)

    client = app_module.app.test_client()
    resp = client.post("/api/pull-data")
    assert resp.status_code == 200
    assert called["ok"] is True


@pytest.mark.buttons
# test_post_update_analysis_not_busy(app_module)
def test_post_update_analysis_not_busy(app_module):
    app_module.is_pulling = False
    client = app_module.app.test_client()
    resp = client.post("/api/update-analysis")
    assert resp.status_code == 200


@pytest.mark.buttons
# test_busy_gating_blocks_actions(app_module)
def test_busy_gating_blocks_actions(app_module):
    app_module.is_pulling = True
    client = app_module.app.test_client()

    resp_update = client.post("/api/update-analysis")
    assert resp_update.status_code == 409

    resp_pull = client.post("/api/pull-data")
    assert resp_pull.status_code == 409

    app_module.is_pulling = False
