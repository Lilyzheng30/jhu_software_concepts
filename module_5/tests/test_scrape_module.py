"""Tests scrape parsing and edge-case behavior with mocked HTML/network calls."""

import importlib
import os
import runpy
import sys

from bs4 import BeautifulSoup
import pytest

SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

scrape_mod = importlib.import_module("module_2.scrape")
parse_row = scrape_mod.parse_row
parse_detail_page = scrape_mod.parse_detail_page
scrape_data = scrape_mod.scrape_data


class _FakeResp:
    """Simple response wrapper exposing .read() bytes for urlopen mocks."""

    def __init__(self, html):
        """Store HTML text that will be returned on read()."""
        self._html = html

    def read(self):
        """Return HTML as UTF-8 bytes."""
        return self._html.encode("utf-8")

    def close(self):
        """Provide a no-op close method for API compatibility."""
        return None


@pytest.mark.db
def test_parse_row_and_meta():
    """parse_row extracts detail URL and semester metadata from adjacent rows."""
    html = """
    <table>
      <tr><th>Program</th><th>University</th><th>Date</th><th>Decision</th></tr>
      <tr>
        <td>CS</td><td>JHU</td><td>Jan 1, 2025</td><td>Accepted on Jan 2, 2025</td>
        <td><a href="/survey/123">Link</a></td>
      </tr>
      <tr><td colspan="4">Fall 2026 American</td></tr>
    </table>
    """
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.find_all("tr")
    entry = parse_row(rows[1], rows[2])

    assert entry["semester_year_start_raw"] == "Fall 2026"
    assert entry["url"] == "https://www.thegradcafe.com/survey/123"


@pytest.mark.db
def test_parse_row_short_row():
    """parse_row returns None for malformed table rows."""
    row = BeautifulSoup("<tr><td>Only</td></tr>", "html.parser").find("tr")
    assert parse_row(row, None) is None


@pytest.mark.db
def test_extract_semester_no_match():
    """_extract_semester returns None when term text is missing."""
    extract_fn = getattr(scrape_mod, "_extract_semester")
    assert extract_fn("No semester provided") is None


@pytest.mark.db
def test_parse_detail_page(monkeypatch):
    """parse_detail_page parses GPA/program/degree/comments/GRE fields."""
    html = """
    <main>
      <dl>
        <div><dt>Undergrad GPA</dt><dd>3.9</dd></div>
        <div><dt>Program</dt><dd>Computer Science</dd></div>
        <div><dt>Degree Type</dt><dd>Masters</dd></div>
        <div><dt>Note</dt><dd>Test</dd></div>
        <div><dt>Degree's Country of Origin</dt><dd>American</dd></div>
        <ul>
          <li><span>GRE General</span><span>330</span></li>
          <li><span>GRE Verbal</span><span>165</span></li>
          <li><span>Analytical Writing</span><span>4.5</span></li>
        </ul>
      </dl>
    </main>
    """

    def _fake_urlopen(_request_obj):
        return _FakeResp(html)

    monkeypatch.setattr("module_2.scrape.request.urlopen", _fake_urlopen)

    data = parse_detail_page("https://example.com")
    assert data["gpa_raw"] == "3.9"
    assert data["program_raw"] == "Computer Science"
    assert data["degree_type_raw"] == "Masters"
    assert data["comments_raw"] == "Test"
    assert data["international_american_raw"] == "American"
    assert data["gre_score_raw"] == "330"
    assert data["gre_v_score_raw"] == "165"
    assert data["gre_aw_raw"] == "4.5"


@pytest.mark.db
def test_parse_detail_page_missing_sections(monkeypatch):
    """parse_detail_page returns empty dict when expected sections are absent."""

    def _fake_urlopen_missing_main(_request_obj):
        return _FakeResp("<html><body>No main here</body></html>")

    monkeypatch.setattr("module_2.scrape.request.urlopen", _fake_urlopen_missing_main)
    data = parse_detail_page("https://example.com/missing")
    assert not data

    def _fake_urlopen_missing_dl(_request_obj):
        return _FakeResp("<main><p>No dl here</p></main>")

    monkeypatch.setattr("module_2.scrape.request.urlopen", _fake_urlopen_missing_dl)
    data2 = parse_detail_page("https://example.com/missing2")
    assert not data2


@pytest.mark.db
def test_parse_detail_page_exception(monkeypatch):
    """parse_detail_page returns empty dict on request exceptions."""

    def _fake_urlopen(_request_obj):
        raise RuntimeError("boom")

    monkeypatch.setattr("module_2.scrape.request.urlopen", _fake_urlopen)
    data = parse_detail_page("https://example.com/error")
    assert not data


@pytest.mark.db
def test_scrape_data_collects_entries(monkeypatch):
    """scrape_data collects rows and merges detail-page fields."""
    list_html = """
    <table>
      <tr><th>Program</th><th>University</th><th>Date</th><th>Decision</th></tr>
      <tr>
        <td>CS</td><td>JHU</td><td>Jan 1, 2025</td><td>Accepted on Jan 2, 2025</td>
        <td><a href="/survey/123">Link</a></td>
      </tr>
      <tr><td colspan="4">Fall 2026 American</td></tr>
    </table>
    """
    detail_html = """
    <main><dl>
      <div><dt>Undergrad GPA</dt><dd>3.9</dd></div>
    </dl></main>
    """

    calls = {"n": 0}

    def _fake_urlopen(_request_obj):
        calls["n"] += 1
        if calls["n"] == 1:
            return _FakeResp(list_html)
        return _FakeResp(detail_html)

    monkeypatch.setattr("module_2.scrape.request.urlopen", _fake_urlopen)

    entries = scrape_data(existing_urls=set(), stop_after_existing=1)
    assert len(entries) == 1
    assert entries[0]["semester_year_start_raw"] == "Fall 2026"
    assert entries[0]["gpa_raw"] == "3.9"


@pytest.mark.db
def test_scrape_data_breaks_on_no_rows(monkeypatch):
    """scrape_data returns no entries when listing table has no data rows."""

    def _fake_urlopen(_request_obj):
        return _FakeResp("<table><tr><th>Header</th></tr></table>")

    monkeypatch.setattr("module_2.scrape.request.urlopen", _fake_urlopen)
    entries = scrape_data(existing_urls=set(), stop_after_existing=1)
    assert not entries


@pytest.mark.db
def test_scrape_data_handles_fetch_error(monkeypatch):
    """scrape_data returns no entries when list page fetch fails."""

    def _fake_urlopen(_request_obj):
        raise RuntimeError("boom")

    monkeypatch.setattr("module_2.scrape.request.urlopen", _fake_urlopen)
    entries = scrape_data(existing_urls=set(), stop_after_existing=1)
    assert not entries


@pytest.mark.db
def test_scrape_data_stops_on_existing(monkeypatch):
    """scrape_data stops when first listing URL is already known."""
    list_html = """
    <table>
      <tr><th>Program</th><th>University</th><th>Date</th><th>Decision</th></tr>
      <tr>
        <td>CS</td><td>JHU</td><td>Jan 1, 2025</td><td>Accepted on Jan 2, 2025</td>
        <td><a href="/survey/123">Link</a></td>
      </tr>
    </table>
    """

    def _fake_urlopen(_request_obj):
        return _FakeResp(list_html)

    monkeypatch.setattr("module_2.scrape.request.urlopen", _fake_urlopen)
    entries = scrape_data(
        existing_urls={"https://www.thegradcafe.com/survey/123"},
        stop_after_existing=1,
    )
    assert not entries


@pytest.mark.db
def test_save_data_and_run_scrape(monkeypatch, tmp_path):
    """run_scrape calls scrape_data and save_data with expected values."""

    def _fake_scrape_data(**_kwargs):
        return [{"url": "u1"}]

    def _fake_save_data(*_args, **_kwargs):
        return None

    monkeypatch.setattr(scrape_mod, "scrape_data", _fake_scrape_data)
    monkeypatch.setattr(scrape_mod, "save_data", _fake_save_data)

    out_path = tmp_path / "out.json"
    entries = scrape_mod.run_scrape(existing_urls=set(), filename=str(out_path))
    assert entries == [{"url": "u1"}]


@pytest.mark.db
def test_scrape_main():
    """module_2.scrape __main__ executes safely with injected run_scrape."""

    def _fake_run_scrape(**_kwargs):
        return []

    runpy.run_module(
        "module_2.scrape",
        run_name="__main__",
        init_globals={"run_scrape": _fake_run_scrape},
    )


@pytest.mark.db
def test_existing_continue_branch(monkeypatch):
    """When stop_after_existing > 1, existing URL path still continues correctly."""
    list_html = """
    <table>
      <tr><th>Program</th><th>University</th><th>Date</th><th>Decision</th></tr>
      <tr>
        <td>CS</td><td>JHU</td><td>Jan 1, 2025</td><td>Accepted on Jan 2, 2025</td>
        <td><a href="/survey/123">Link</a></td>
      </tr>
    </table>
    """

    def _fake_urlopen(_request_obj):
        return _FakeResp(list_html)

    monkeypatch.setattr("module_2.scrape.request.urlopen", _fake_urlopen)
    entries = scrape_data(
        existing_urls={"https://www.thegradcafe.com/survey/123"},
        stop_after_existing=2,
    )
    assert not entries


@pytest.mark.db
def test_parse_detail_page_short_spans(monkeypatch):
    """parse_detail_page handles malformed span rows safely."""
    html = """
    <main>
      <dl>
        <ul>
          <li><span>Only one</span></li>
        </ul>
      </dl>
    </main>
    """

    def _fake_urlopen(_request_obj):
        return _FakeResp(html)

    monkeypatch.setattr("module_2.scrape.request.urlopen", _fake_urlopen)
    data = parse_detail_page("https://example.com/short")
    assert not data
