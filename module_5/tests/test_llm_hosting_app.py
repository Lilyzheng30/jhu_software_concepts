"""Tests for module_2.llm_hosting.app behavior and CLI/HTTP paths."""

import importlib
import json
import os
import runpy
import sys
import types

import flask
import pytest

SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)


_FAKE_RESPONSE_JSON = {
    "standardized_program": "Computer Science",
    "standardized_university": "Test University",
}


def _fake_hf_hub_download(**_kwargs):
    """Return a fake local model path for tests."""
    return "models/fake.gguf"


def _fake_chat_completion(**_kwargs):
    """Return valid JSON payload in the shape expected by the app."""
    return {
        "choices": [
            {
                "message": {
                    "content": json.dumps(_FAKE_RESPONSE_JSON),
                }
            }
        ]
    }


class _FakeLlama:
    """Tiny fake llama class used for import-time dependency stubbing."""

    def __init__(self, **_kwargs):
        """Build a no-op instance."""

    def create_chat_completion(self, **_kwargs):
        """Return deterministic standardized output."""
        return _fake_chat_completion()

    def ping(self):
        """Return a trivial health value for lint-friendly public API shape."""
        return True


sys.modules["huggingface_hub"] = types.SimpleNamespace(
    hf_hub_download=_fake_hf_hub_download,
)
sys.modules["llama_cpp"] = types.SimpleNamespace(Llama=_FakeLlama)

llm_app = importlib.import_module("module_2.llm_hosting.app")


def _call_private(name, *args, **kwargs):
    """Call a private helper from llm_app by name."""
    return getattr(llm_app, name)(*args, **kwargs)


@pytest.mark.db
def test_split_fallback_and_normalize():
    """Split fallback text and normalize program/university names."""
    prog, uni = _call_private("_split_fallback", "Information, McG")
    assert "Information" in prog
    assert "mcgill" in uni.lower()

    assert _call_private("_post_normalize_program", "Mathematic") == "Mathematics"
    normalized = _call_private(
        "_post_normalize_university",
        "University Of British Columbia",
    )
    assert normalized == "University of British Columbia"

    _unused_prog, uni2 = _call_private("_split_fallback", "Math, UBC")
    assert "University of British Columbia" in uni2
    _unused_prog2, uni3 = _call_private("_split_fallback", "Math")
    assert uni3 == "Unknown"


@pytest.mark.db
def test_build_program_text_and_fallback():
    """Build display text and fallback university mappings."""
    row = {"program": "CS", "university": "JHU"}
    assert _call_private("_build_program_text", row) == "CS, JHU"

    uni = _call_private(
        "_fallback_university",
        {"university": "McGill University"},
        "Unknown",
    )
    assert "mcgill" in uni.lower()

    assert _call_private("_fallback_university", {"university": "X"}, "") == ""
    assert _call_private("_build_program_text", {"program": "CS"}) == "CS"


@pytest.mark.db
def test_call_llm_parses_json(monkeypatch):
    """Parse model JSON output into standardized keys."""

    def _load_llm_stub():
        return types.SimpleNamespace(create_chat_completion=_fake_chat_completion)

    monkeypatch.setattr(llm_app, "_load_llm", _load_llm_stub)
    result = _call_private("_call_llm", "Computer Science, Test University")
    assert result["standardized_program"] == "Computer Science"
    assert result["standardized_university"] == "Test University"


@pytest.mark.db
def test_call_llm_fallback_path(monkeypatch):
    """Use fallback parser if the model output is not JSON."""

    def _bad_chat_completion(**_kwargs):
        return {"choices": [{"message": {"content": "not json"}}]}

    def _load_bad_llm_stub():
        return types.SimpleNamespace(create_chat_completion=_bad_chat_completion)

    monkeypatch.setattr(llm_app, "_load_llm", _load_bad_llm_stub)
    result = _call_private("_call_llm", "Information, McG")
    assert "Information" in result["standardized_program"]


@pytest.mark.db
def test_normalize_input():
    """Normalize both list and dict payload shapes."""
    assert _call_private("_normalize_input", []) == []
    assert _call_private("_normalize_input", {"rows": [{"a": 1}]}) == [{"a": 1}]
    assert _call_private("_normalize_input", {"bad": 1}) == []


@pytest.mark.db
def test_standardize_endpoint(monkeypatch):
    """POST /standardize returns rows with llm-generated fields."""

    def _load_llm_stub():
        return types.SimpleNamespace(create_chat_completion=_fake_chat_completion)

    monkeypatch.setattr(llm_app, "_load_llm", _load_llm_stub)

    client = llm_app.app.test_client()
    payload = {"rows": [{"program": "CS", "university": "Test University"}]}
    resp = client.post(
        "/standardize",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["rows"][0]["llm-generated-program"] == "Computer Science"


@pytest.mark.db
def test_health_endpoint():
    """GET / returns an ok=true payload."""
    client = llm_app.app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.get_json()["ok"] is True


@pytest.mark.db
def test_cli_process_file(monkeypatch, tmp_path):
    """CLI file processing writes one JSONL row per input row."""

    def _load_llm_stub():
        return types.SimpleNamespace(create_chat_completion=_fake_chat_completion)

    monkeypatch.setattr(llm_app, "_load_llm", _load_llm_stub)

    inp = tmp_path / "in.json"
    out = tmp_path / "out.jsonl"
    inp.write_text(json.dumps([{"program": "CS", "university": "Test University"}]))

    llm_app.cli_process_file(str(inp), str(out), append=False, to_stdout=False)
    lines = out.read_text().strip().splitlines()
    assert len(lines) == 1


@pytest.mark.db
def test_cli_process_file_stdout(monkeypatch, tmp_path, capsys):
    """CLI file processing can write JSONL to stdout."""

    def _load_llm_stub():
        return types.SimpleNamespace(create_chat_completion=_fake_chat_completion)

    monkeypatch.setattr(llm_app, "_load_llm", _load_llm_stub)

    inp = tmp_path / "in.json"
    inp.write_text(json.dumps([{"program": "CS", "university": "Test University"}]))

    llm_app.cli_process_file(str(inp), None, append=False, to_stdout=True)
    captured = capsys.readouterr().out.strip()
    assert captured


@pytest.mark.db
def test_best_match_and_load_llm(monkeypatch):
    """Cover llm cache and best-match helper behavior."""
    setattr(llm_app, "_LLM", None)
    monkeypatch.setattr(llm_app, "hf_hub_download", _fake_hf_hub_download)
    monkeypatch.setattr(llm_app, "Llama", _FakeLlama)

    llm = _call_private("_load_llm")
    assert llm is not None
    assert _call_private("_best_match", "Math", ["Math", "Physics"]) == "Math"
    assert _call_private("_best_match", "Math", []) is None
    assert _call_private("_load_llm") is llm


@pytest.mark.db
def test_read_lines_and_post_normalize_paths(tmp_path, monkeypatch):
    """Cover read-lines and post-normalization branches."""
    path_obj = tmp_path / "lines.txt"
    path_obj.write_text("A\n\nB\n")
    lines = _call_private("_read_lines", str(path_obj))
    assert lines == ["A", "B"]

    monkeypatch.setattr(llm_app, "CANON_PROGS", ["Computer Science"])
    assert _call_private("_post_normalize_program", "Computer Science") == "Computer Science"

    monkeypatch.setattr(llm_app, "CANON_UNIS", ["McGill University"])
    assert _call_private("_post_normalize_university", "McG") == "McGill University"
    assert _call_private(
        "_post_normalize_university",
        "McGill University",
    ) == "McGill University"


@pytest.mark.db
def test_post_normalize_university_canon_direct(monkeypatch):
    """Direct canonical university should remain unchanged."""
    monkeypatch.setattr(llm_app, "CANON_UNIS", ["Stanford University"])
    assert (
        _call_private("_post_normalize_university", "Stanford University")
        == "Stanford University"
    )


@pytest.mark.db
def test_main_serve_branch_safe(monkeypatch):
    """Running __main__ with --serve should call Flask.run safely."""

    def _fake_run(*_args, **_kwargs):
        return None

    monkeypatch.setattr(flask.Flask, "run", _fake_run)
    monkeypatch.setattr(sys, "argv", ["app.py", "--serve"])
    runpy.run_module("module_2.llm_hosting.app", run_name="__main__")


@pytest.mark.db
def test_main_cli_branch_safe(monkeypatch, tmp_path):
    """Running __main__ in CLI mode should process input without crash."""
    inp = tmp_path / "in.json"
    out_path = tmp_path / "o.jsonl"
    inp.write_text(json.dumps([{"program": "CS", "university": "Test University"}]))

    monkeypatch.setattr(sys, "argv", ["app.py", "--file", str(inp), "--out", str(out_path)])

    def _fake_cli(*_args, **_kwargs):
        return None

    runpy.run_module(
        "module_2.llm_hosting.app",
        run_name="__main__",
        init_globals={"_cli_process_file": _fake_cli},
    )
