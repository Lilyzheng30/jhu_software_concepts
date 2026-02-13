import os
import sys
import json
import types
import pytest

SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

# Stub heavy deps before importing the module.
fake_hf = types.SimpleNamespace(hf_hub_download=lambda **_: "models/fake.gguf")

class _FakeLlama:
    def __init__(self, **_):
        return None

    def create_chat_completion(self, **_):
        return {
            "choices": [
                {"message": {"content": "{\"standardized_program\": \"Computer Science\", \"standardized_university\": \"Test University\"}"}}
            ]
        }

sys.modules["huggingface_hub"] = fake_hf
sys.modules["llama_cpp"] = types.SimpleNamespace(Llama=_FakeLlama)

from module_2.llm_hosting import app as llm_app


class _FakeLLM:
    def create_chat_completion(self, **_):
        return {
            "choices": [
                {"message": {"content": "{\"standardized_program\": \"Computer Science\", \"standardized_university\": \"Test University\"}"}}
            ]
        }


@pytest.mark.db
def test_split_fallback_and_normalize():
    prog, uni = llm_app._split_fallback("Information, McG")
    assert "Information" in prog
    assert "mcgill" in uni.lower()

    assert llm_app._post_normalize_program("Mathematic") == "Mathematics"
    assert llm_app._post_normalize_university("University Of British Columbia") == "University of British Columbia"
    # UBC expansion path in _split_fallback
    prog2, uni2 = llm_app._split_fallback("Math, UBC")
    assert "University of British Columbia" in uni2
    # Unknown university fallback
    prog3, uni3 = llm_app._split_fallback("Math")
    assert uni3 == "Unknown"


@pytest.mark.db
def test_build_program_text_and_fallback():
    row = {"program": "CS", "university": "JHU"}
    assert llm_app._build_program_text(row) == "CS, JHU"

    uni = llm_app._fallback_university({"university": "McGill University"}, "Unknown")
    assert "mcgill" in uni.lower()
    # Empty model university
    assert llm_app._fallback_university({"university": "X"}, "") == ""
    # Only program present
    assert llm_app._build_program_text({"program": "CS"}) == "CS"


@pytest.mark.db
def test_call_llm_parses_json(monkeypatch):
    monkeypatch.setattr(llm_app, "_load_llm", lambda: _FakeLLM())
    result = llm_app._call_llm("Computer Science, Test University")
    assert result["standardized_program"] == "Computer Science"
    assert result["standardized_university"] == "Test University"


@pytest.mark.db
def test_call_llm_fallback_path(monkeypatch):
    class BadLLM:
        def create_chat_completion(self, **_):
            return {"choices": [{"message": {"content": "not json"}}]}

    monkeypatch.setattr(llm_app, "_load_llm", lambda: BadLLM())
    result = llm_app._call_llm("Information, McG")
    assert "Information" in result["standardized_program"]


@pytest.mark.db
def test_normalize_input():
    assert llm_app._normalize_input([]) == []
    assert llm_app._normalize_input({"rows": [{"a": 1}]}) == [{"a": 1}]
    assert llm_app._normalize_input({"bad": 1}) == []


@pytest.mark.db
def test_standardize_endpoint(monkeypatch):
    monkeypatch.setattr(llm_app, "_load_llm", lambda: _FakeLLM())

    client = llm_app.app.test_client()
    resp = client.post(
        "/standardize",
        data=json.dumps({"rows": [{"program": "CS", "university": "Test University"}]}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["rows"][0]["llm-generated-program"] == "Computer Science"


@pytest.mark.db
def test_health_endpoint():
    client = llm_app.app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.get_json()["ok"] is True


@pytest.mark.db
def test_cli_process_file(monkeypatch, tmp_path):
    monkeypatch.setattr(llm_app, "_load_llm", lambda: _FakeLLM())

    inp = tmp_path / "in.json"
    out = tmp_path / "out.jsonl"
    inp.write_text(json.dumps([{"program": "CS", "university": "Test University"}]))

    llm_app._cli_process_file(str(inp), str(out), append=False, to_stdout=False)
    lines = out.read_text().strip().splitlines()
    assert len(lines) == 1


@pytest.mark.db
def test_best_match_and_load_llm(monkeypatch):
    llm_app._LLM = None
    monkeypatch.setattr(llm_app, "hf_hub_download", lambda **_: "models/fake.gguf")
    monkeypatch.setattr(llm_app, "Llama", _FakeLlama)
    llm = llm_app._load_llm()
    assert llm is not None
    assert llm_app._best_match("Math", ["Math", "Physics"]) == "Math"
    # _best_match with empty candidates
    assert llm_app._best_match("Math", []) is None
    # reuse cached _LLM
    assert llm_app._load_llm() is llm


@pytest.mark.db
def test_read_lines_and_post_normalize_paths(tmp_path, monkeypatch):
    p = tmp_path / "lines.txt"
    p.write_text("A\n\nB\n")
    lines = llm_app._read_lines(str(p))
    assert lines == ["A", "B"]

    # Canonical program present
    monkeypatch.setattr(llm_app, "CANON_PROGS", ["Computer Science"])
    assert llm_app._post_normalize_program("Computer Science") == "Computer Science"

    # Abbreviation path and canonical university path
    monkeypatch.setattr(llm_app, "CANON_UNIS", ["McGill University"])
    assert llm_app._post_normalize_university("McG") == "McGill University"
    assert llm_app._post_normalize_university("McGill University") == "McGill University"
    # Direct canonical match to hit line 203
    assert llm_app._post_normalize_university("McGill University") == "McGill University"


@pytest.mark.db
def test_post_normalize_university_canon_direct(monkeypatch):
    monkeypatch.setattr(llm_app, "CANON_UNIS", ["Stanford University"])
    assert llm_app._post_normalize_university("Stanford University") == "Stanford University"


@pytest.mark.db
def test_main_serve_branch_safe(monkeypatch):
    import runpy
    import flask

    monkeypatch.setattr(flask.Flask, "run", lambda *_, **__: None)
    monkeypatch.setattr(sys, "argv", ["app.py", "--serve"])
    runpy.run_module("module_2.llm_hosting.app", run_name="__main__")


@pytest.mark.db
def test_main_cli_branch_safe(monkeypatch, tmp_path):
    import runpy

    inp = tmp_path / "in.json"
    inp.write_text(json.dumps([{"program": "CS", "university": "Test University"}]))

    monkeypatch.setattr(sys, "argv", ["app.py", "--file", str(inp), "--out", str(tmp_path / "o.jsonl")])

    def fake_cli(*_, **__):
        return None

    runpy.run_module(
        "module_2.llm_hosting.app",
        run_name="__main__",
        init_globals={"_cli_process_file": fake_cli},
    )
