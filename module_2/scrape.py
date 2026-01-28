from bs4 import BeautifulSoup
from urllib import request
import json

# pulls data from grad cafe
def scrape_data():
    all_entries = []
    base_url = "https://www.thegradcafe.com/survey/"

    for page_num in range(1, 4):
        full_url = base_url + "?page=" + str(page_num)

        req = request.Request(full_url)
        req.add_header("User-Agent", "Mozilla/5.0")

        page = request.urlopen(req)
        html = page.read().decode("utf-8")

        soup = BeautifulSoup(html, "html.parser")

        table = soup.find("table")
        if not table:
            break

        rows = table.find_all("tr")[1:]
        if not rows:
            break
        
        for table_row in rows:
            entry = parse_row(table_row)
            if entry:
                if entry["url"]:
                    extra = parse_detail_page(entry["url"])
                    entry.update(extra)
                all_entries.append(entry)

    return all_entries



def parse_row(table_row):
    tds = table_row.find_all("td")
    if len(tds) < 4:
        return None

    university_raw = tds[0].get_text(" ", strip=True)
    program_raw = tds[1].get_text(" ", strip=True)
    date_raw = tds[2].get_text(" ", strip=True)
    decision_raw = tds[3].get_text(" ", strip=True)

    a = tds[4].find("a")
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
        "semester_year_start_raw": None,
        "international_american_raw": None,
        "gre_score_raw": None,
        "gre_v_score_raw": None,
        "degree_type_raw": None,
        "gpa_raw": None,
        "gre_aw_raw": None,
    }

def parse_detail_page(url):
    req = request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0")

    page = request.urlopen(req)
    html = page.read().decode("utf-8")
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

        # li = block.find("li")
        # if not li:
        #     continue
        # figure out the last box whic has a list of information 

        label = dt.get_text(" ", strip=True).lower()
        value = dd.get_text(" ", strip=True)

        if "undergrad gpa" in label:
            detail_data["gpa_raw"] = value
        elif "program" in label:
            detail_data["program_raw"] = value
        elif "gre general" in label:
            detail_data["gre_score_raw"] = value
        elif "degree type" in label:
            detail_data["degree_type_raw"] = value
        elif "note" in label:
            detail_data["comments_raw"] = value
        elif "gre verbal" in label:
            detail_data["gre_v_score_raw"] = value
        elif "analytical writing" in label:
            detail_data["gre_aw_raw"] = value
        elif "degree's country of origin" in label:
            if value == "American":
                detail_data["international_american_raw"] = value
            else:
                detail_data["international_american_raw"] = 'International'


    return detail_data


#add fall 2026 and also like figure out status and acceptance date thing 


def save_data(data, filename="applicant_data.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


entries = scrape_data()
print("Number of entries:", len(entries))
print("First entry dict:", entries[0] if entries else "None")
save_data(entries)
