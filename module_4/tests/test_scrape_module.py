# Tests scrape parsing and edge cases with mocked HTML.
import os
import sys
import pytest

SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

from module_2.scrape import parse_row, parse_detail_page, scrape_data


class _FakeResp:
    def __init__(self, html):
        self._html = html

    def read(self):
        return self._html.encode("utf-8")


@pytest.mark.db
# test_parse_row_and_meta()
def test_parse_row_and_meta():
    from bs4 import BeautifulSoup

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
# test_parse_row_short_row()
def test_parse_row_short_row():
    from bs4 import BeautifulSoup

    html = "<tr><td>Only</td></tr>"
    row = BeautifulSoup(html, "html.parser").find("tr")
    assert parse_row(row, None) is None


@pytest.mark.db
# test_parse_detail_page(monkeypatch)
def test_parse_detail_page(monkeypatch):
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

    def fake_urlopen(req):
        return _FakeResp(html)

    monkeypatch.setattr("module_2.scrape.request.urlopen", fake_urlopen)

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
# test_parse_detail_page_missing_sections(monkeypatch)
def test_parse_detail_page_missing_sections(monkeypatch):
    def fake_urlopen(req):
        return _FakeResp("<html><body>No main here</body></html>")

    monkeypatch.setattr("module_2.scrape.request.urlopen", fake_urlopen)
    data = parse_detail_page("https://example.com/missing")
    assert data == {}

    def fake_urlopen2(req):
        return _FakeResp("<main><p>No dl here</p></main>")

    monkeypatch.setattr("module_2.scrape.request.urlopen", fake_urlopen2)
    data2 = parse_detail_page("https://example.com/missing2")
    assert data2 == {}


@pytest.mark.db
# test_parse_detail_page_exception(monkeypatch)
def test_parse_detail_page_exception(monkeypatch):
    def fake_urlopen(req):
        raise Exception("boom")

    monkeypatch.setattr("module_2.scrape.request.urlopen", fake_urlopen)
    data = parse_detail_page("https://example.com/error")
    assert data == {}


@pytest.mark.db
# test_scrape_data_collects_entries(monkeypatch)
def test_scrape_data_collects_entries(monkeypatch):
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

    def fake_urlopen(req):
        calls["n"] += 1
        if calls["n"] == 1:
            return _FakeResp(list_html)
        return _FakeResp(detail_html)

    monkeypatch.setattr("module_2.scrape.request.urlopen", fake_urlopen)

    entries = scrape_data(existing_urls=set(), stop_after_existing=1)
    assert len(entries) == 1
    assert entries[0]["semester_year_start_raw"] == "Fall 2026"
    assert entries[0]["gpa_raw"] == "3.9"


@pytest.mark.db
# test_scrape_data_breaks_on_no_rows(monkeypatch)
def test_scrape_data_breaks_on_no_rows(monkeypatch):
    html = "<table><tr><th>Header</th></tr></table>"

    def fake_urlopen(req):
        return _FakeResp(html)

    monkeypatch.setattr("module_2.scrape.request.urlopen", fake_urlopen)
    entries = scrape_data(existing_urls=set(), stop_after_existing=1)
    assert entries == []


@pytest.mark.db
# test_scrape_data_handles_fetch_error(monkeypatch)
def test_scrape_data_handles_fetch_error(monkeypatch):
    def fake_urlopen(req):
        raise Exception("boom")

    monkeypatch.setattr("module_2.scrape.request.urlopen", fake_urlopen)

    entries = scrape_data(existing_urls=set(), stop_after_existing=1)
    assert entries == []


@pytest.mark.db
# test_scrape_data_stops_on_existing(monkeypatch)
def test_scrape_data_stops_on_existing(monkeypatch):
    list_html = """
    <table>
      <tr><th>Program</th><th>University</th><th>Date</th><th>Decision</th></tr>
      <tr>
        <td>CS</td><td>JHU</td><td>Jan 1, 2025</td><td>Accepted on Jan 2, 2025</td>
        <td><a href="/survey/123">Link</a></td>
      </tr>
    </table>
    """

    def fake_urlopen(req):
        return _FakeResp(list_html)

    monkeypatch.setattr("module_2.scrape.request.urlopen", fake_urlopen)

    entries = scrape_data(existing_urls={"https://www.thegradcafe.com/survey/123"}, stop_after_existing=1)
    assert entries == []


@pytest.mark.db
# test_save_data_and_run_scrape(monkeypatch, tmp_path)
def test_save_data_and_run_scrape(monkeypatch, tmp_path):
    from module_2 import scrape as scrape_mod

    monkeypatch.setattr(scrape_mod, "scrape_data", lambda **_: [{"url": "u1"}])
    monkeypatch.setattr(scrape_mod, "save_data", lambda *_, **__: None)

    out = tmp_path / "out.json"
    entries = scrape_mod.run_scrape(existing_urls=set(), filename=str(out))
    assert entries == [{"url": "u1"}]


@pytest.mark.db
# test_scrape_main(monkeypatch)
def test_scrape_main(monkeypatch):
    import runpy

    runpy.run_module(
        "module_2.scrape",
        run_name="__main__",
        init_globals={"run_scrape": lambda **_: []},
    )


@pytest.mark.db
# test_existing_continue_branch(monkeypatch)
def test_existing_continue_branch(monkeypatch):
    list_html = """
    <table>
      <tr><th>Program</th><th>University</th><th>Date</th><th>Decision</th></tr>
      <tr>
        <td>CS</td><td>JHU</td><td>Jan 1, 2025</td><td>Accepted on Jan 2, 2025</td>
        <td><a href="/survey/123">Link</a></td>
      </tr>
    </table>
    """

    def fake_urlopen(req):
        return _FakeResp(list_html)

    monkeypatch.setattr("module_2.scrape.request.urlopen", fake_urlopen)
    # stop_after_existing=2 ensures it hits the continue branch (59-60) before returning
    entries = scrape_data(existing_urls={"https://www.thegradcafe.com/survey/123"}, stop_after_existing=2)
    assert entries == []


@pytest.mark.db
# test_parse_detail_page_short_spans(monkeypatch)
def test_parse_detail_page_short_spans(monkeypatch):
    html = """
    <main>
      <dl>
        <ul>
          <li><span>Only one</span></li>
        </ul>
      </dl>
    </main>
    """

    def fake_urlopen(req):
        return _FakeResp(html)

    monkeypatch.setattr("module_2.scrape.request.urlopen", fake_urlopen)
    data = parse_detail_page("https://example.com/short")
    assert data == {}
