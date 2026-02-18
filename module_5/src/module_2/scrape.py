"""Scrape GradCafe survey pages and extract application records."""

import json
from contextlib import suppress
from urllib import request

from bs4 import BeautifulSoup


def _fetch_html(url):
    """Fetch and decode HTML for a URL with a browser-like user agent."""
    req = request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0")
    page = request.urlopen(req)
    if hasattr(page, "__enter__") and hasattr(page, "__exit__"):
        with page as opened:
            return opened.read().decode("utf-8")
    return page.read().decode("utf-8")


def _has_meta_info(row_text):
    """Return True when row text likely contains semester/citizenship metadata."""
    lowered = row_text.lower()
    markers = ("fall", "spring", "summer", "winter", "international", "american")
    return any(marker in lowered for marker in markers)


def _extract_semester(meta_text):
    """Extract season and year (for example, 'Fall 2026') from free text."""
    tokens = meta_text.split()
    for idx in range(len(tokens) - 1):
        season = tokens[idx].lower()
        year = tokens[idx + 1]
        if season in {"fall", "spring", "summer", "winter"} and year.isdigit() and len(year) == 4:
            return f"{tokens[idx]} {year}"
    return None


def _apply_detail_field(detail_data, label, value):
    """Map one detail-page label/value pair into output fields."""
    field_map = {
        "undergrad gpa": "gpa_raw",
        "program": "program_raw",
        "degree type": "degree_type_raw",
        "note": "comments_raw",
    }
    for marker, key in field_map.items():
        if marker in label:
            detail_data[key] = value
            return
    if "degree's country of origin" in label:
        detail_data["international_american_raw"] = (
            "American" if value == "American" else "International"
        )


def _apply_gre_field(detail_data, label, value):
    """Map GRE labels while preserving the first observed value per field."""
    rules = (
        ("gre general", "gre_score_raw"),
        ("gre verbal", "gre_v_score_raw"),
        ("analytical writing", "gre_aw_raw"),
    )
    for marker, key in rules:
        if marker in label and not detail_data.get(key):
            detail_data[key] = value
            return


def _extract_detail_from_dl(dl):
    """Parse detail fields from a detail-page definition list."""
    detail_data = {}

    for block in dl.find_all("div"):
        dt = block.find("dt")
        dd = block.find("dd")
        if not dt or not dd:
            continue

        label = dt.get_text(" ", strip=True).lower()
        value = dd.get_text(" ", strip=True)
        _apply_detail_field(detail_data, label, value)

    ul = dl.find("ul")
    if not ul:
        return detail_data

    for li in ul.find_all("li"):
        spans = li.find_all("span")
        if len(spans) < 2:
            continue

        label = spans[0].get_text(" ", strip=True).lower()
        value = spans[1].get_text(" ", strip=True)
        _apply_gre_field(detail_data, label, value)

    return detail_data


def _parse_page_rows(rows, all_entries, existing_urls, consecutive_existing, stop_after_existing):
    """Parse all listing rows on one page."""
    row_index = 0
    while row_index < len(rows):
        main_row = rows[row_index]
        meta_row = None
        step = 1

        if row_index + 1 < len(rows):
            next_text = rows[row_index + 1].get_text(" ", strip=True)
            if _has_meta_info(next_text):
                meta_row = rows[row_index + 1]
                step = 2

        entry = parse_row(main_row, meta_row)
        if entry:
            entry_url = entry.get("url")
            if entry_url and entry_url in existing_urls:
                consecutive_existing += 1
                if consecutive_existing >= stop_after_existing:
                    return consecutive_existing, True
                row_index += step
                continue

            consecutive_existing = 0
            if entry_url:
                entry.update(parse_detail_page(entry_url))
            all_entries.append(entry)

        row_index += step

    return consecutive_existing, False


def scrape_data(existing_urls=None, stop_after_existing=100):
    """Scrape listing pages and collect rows until stop threshold for known URLs."""
    all_entries = []
    existing_urls = existing_urls or set()
    consecutive_existing = 0
    base_url = "https://www.thegradcafe.com/survey/"

    for page_num in range(1, 100):
        full_url = f"{base_url}?page={page_num}"
        html = None
        with suppress(Exception):
            html = _fetch_html(full_url)
        if html is None:
            print("Page fetch failed:", page_num)
            continue

        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        if not table:
            break

        rows = table.find_all("tr")[1:]
        if not rows:
            break

        consecutive_existing, should_stop = _parse_page_rows(
            rows,
            all_entries,
            existing_urls,
            consecutive_existing,
            stop_after_existing,
        )
        if should_stop:
            return all_entries

    return all_entries


def parse_row(main_row, meta_row):
    """Parse one listing row and optional metadata row into raw schema fields."""
    tds = main_row.find_all("td")
    if len(tds) < 4:
        return None

    university_raw = tds[0].get_text(" ", strip=True)
    date_raw = tds[2].get_text(" ", strip=True)
    decision_raw = tds[3].get_text(" ", strip=True)

    semester = None
    if meta_row:
        semester = _extract_semester(meta_row.get_text(" ", strip=True))

    url = None
    link = main_row.find("a")
    if link and link.has_attr("href"):
        url = f"https://www.thegradcafe.com{link['href']}"

    return {
        "program_raw": None,
        "university_raw": university_raw,
        "comments_raw": None,
        "date_added_raw": date_raw,
        "url": url,
        "applicant_status_raw": decision_raw,
        "semester_year_start_raw": semester,
        "international_american_raw": None,
        "gre_score_raw": None,
        "gre_v_score_raw": None,
        "degree_type_raw": None,
        "gpa_raw": None,
        "gre_aw_raw": None,
    }


def parse_detail_page(url):
    """Fetch and parse a detail page to augment listing-row fields."""
    html = None
    with suppress(Exception):
        html = _fetch_html(url)

    if html is None:
        return {}

    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main")
    if not main:
        return {}

    dl = main.find("dl")
    if not dl:
        return {}

    return _extract_detail_from_dl(dl)


def save_data(data, filename="applicant_data.json"):
    """Persist scraped rows as JSON."""
    with open(filename, "w", encoding="utf-8") as file_out:
        json.dump(data, file_out, indent=2, ensure_ascii=False)


def run_scrape(existing_urls=None, filename="applicant_data.json"):
    """Run scrape pipeline and write output file."""
    entries = scrape_data(existing_urls=existing_urls)
    print("Number of entries:", len(entries))
    print("First entry dict:", entries[0] if entries else "None")
    save_data(entries, filename)
    return entries


if __name__ == "__main__":
    run_scrape()
