from bs4 import BeautifulSoup
from urllib import request
import json

# pulls data from grad cafe
def scrape_data():
    all_entries = []
    base_url = "https://www.thegradcafe.com/survey/"

    for page_num in range(3, 1605):
        full_url = base_url + "?page=" + str(page_num)

        # Set a user-agent to reduce blocking.
        req = request.Request(full_url)
        req.add_header("User-Agent", "Mozilla/5.0")

        try:
            page = request.urlopen(req)
            html = page.read().decode("utf-8")
        except Exception as e:
            print("Page fetch failed:", page_num, e)
            continue

        # Parse the listing page HTML.
        soup = BeautifulSoup(html, "html.parser")

        table = soup.find("table")
        if not table:
            break

        rows = table.find_all("tr")[1:]
        if not rows:
            break
        
        meta_row = None
        i = 0
        while i < len(rows):
            main_row = rows[i]

            meta_row = None
            i_step = 1

            if i + 1 < len(rows):
                next_text = rows[i + 1].get_text(" ", strip=True).lower()
                if ("fall" in next_text or "spring" in next_text or "summer" in next_text or "winter" in next_text or "international" in next_text or "american" in next_text):
                    # Meta row contains term/citizenship info for the row above.
                    meta_row = rows[i + 1]
                    i_step = 2

            entry = parse_row(main_row, meta_row)
            if entry:
                if entry["url"]:
                    extra = parse_detail_page(entry["url"])
                    entry.update(extra)
                all_entries.append(entry)

            i += i_step

    return all_entries



def parse_row(main_row, meta_row):
    tds = main_row.find_all("td")
    if len(tds) < 4:
        return None

    university_raw = tds[0].get_text(" ", strip=True)
    date_raw = tds[2].get_text(" ", strip=True)
    decision_raw = tds[3].get_text(" ", strip=True)

    # Extract semester/year from the meta row if present.
    semester = None
    if meta_row:
        meta_text = meta_row.get_text(" ", strip=True)
        tokens = meta_text.split()

        for j in range(len(tokens) - 1):
            season = tokens[j].lower()
            year = tokens[j + 1]

            if season in ["fall", "spring", "summer", "winter"] and year.isdigit() and len(year) == 4:
                semester = tokens[j] + " " + year
                break

    # Detail-page URL 
    link = None
    a = main_row.find("a")
    if a and a.get("href"):
        link = a

    url = None
    if link and link.has_attr("href"):
        url = "https://www.thegradcafe.com" + link["href"]

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
    # Fetch detail page for extra fields (program, GPA, GRE).
    req = request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0")

    try:
        page = request.urlopen(req)
        html = page.read().decode("utf-8")
    except Exception as e:
        return {}
    
    soup = BeautifulSoup(html, "html.parser")

    detail_data = {}

    main = soup.find("main")
    if not main:
        return detail_data

    dl = main.find("dl")
    if not dl:
        return detail_data

    for block in dl.find_all("div"):
        dt = block.find("dt")
        dd = block.find("dd")
        if not dt or not dd:
            continue

        label = dt.get_text(" ", strip=True).lower()
        value = dd.get_text(" ", strip=True)

        # Map known labels to raw fields.
        if "undergrad gpa" in label:
            detail_data["gpa_raw"] = value
        elif "program" in label:
            detail_data["program_raw"] = value
        elif "degree type" in label:
            detail_data["degree_type_raw"] = value
        elif "note" in label:
            detail_data["comments_raw"] = value
        elif "degree's country of origin" in label:
            detail_data["international_american_raw"] = "American" if value == "American" else "International"

    ul = dl.find("ul")
    if ul:
        for li in ul.find_all("li"):
            spans = li.find_all("span")
            if len(spans) < 2:
                continue

            label = spans[0].get_text(" ", strip=True).lower()
            value = spans[1].get_text(" ", strip=True)

            if "gre general" in label and not detail_data.get("gre_score_raw"):
                detail_data["gre_score_raw"] = value
            elif "gre verbal" in label and not detail_data.get("gre_v_score_raw"):
                detail_data["gre_v_score_raw"] = value
            elif "analytical writing" in label and not detail_data.get("gre_aw_raw"):
                detail_data["gre_aw_raw"] = value

    return detail_data


def save_data(data, filename="applicant_data.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


entries = scrape_data()
print("Number of entries:", len(entries))
print("First entry dict:", entries[0] if entries else "None")
save_data(entries)
