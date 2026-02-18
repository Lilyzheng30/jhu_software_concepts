"""Clean scraped GradCafe records into a normalized JSON shape."""

import json


def load_data(filename="applicant_data.json"):
    """Load raw scraped entries from JSON."""
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)


# Map scraped field names to cleaner output names.
RENAME = {
    "program_raw": "program",
    "university_raw": "university",
    "comments_raw": "comments",
    "date_added_raw": "date_added",
    "semester_year_start_raw": "semester_year_start",
    "international_american_raw": "citizenship",
    "gre_score_raw": "gre_total",
    "gre_v_score_raw": "gre_verbal",
    "gre_aw_raw": "gre_writing",
    "degree_type_raw": "degree_type",
    "gpa_raw": "gpa",
    "url": "url",
}


def clean_data(entries):
    """Map raw fields to normalized keys and derive acceptance/rejection dates."""
    cleaned = []

    for e in entries:
        row = {}

        # rename keys + normalize strings
        for old_key, new_key in RENAME.items():
            value = e.get(old_key)

            if isinstance(value, str):
                value = value.strip()
                value = value if value != "" else None

            row[new_key] = value

        # normalize GRE zeros to None
        for k in ["gre_total", "gre_verbal", "gre_writing"]:
            if row.get(k) in ["0", "0.0", "0.00"]:
                row[k] = None

        # normalize GPA zeros to None
        if row.get("gpa") in ["0", "0.0", "0.00"]:
            row["gpa"] = None

        # parse applicant status into dates (keep original status too)
        status = e.get("applicant_status_raw")
        row["applicant_status"] = status

        row["acceptance_date"] = None
        row["rejection_date"] = None

        if isinstance(status, str):
            low = status.lower()
            if low.startswith("accepted on"):
                row["acceptance_date"] = status.replace("Accepted on", "").strip()
            elif low.startswith("rejected on"):
                row["rejection_date"] = status.replace("Rejected on", "").strip()

        cleaned.append(row)

    return cleaned


def save_data(data, filename="llm_extend_applicant_data.json"):
    """Write normalized entries to JSON for downstream LLM processing."""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def run_clean(input_file="applicant_data.json", output_file="llm_extend_applicant_data.json"):
    """Run the full clean pipeline and return cleaned records."""
    entries = load_data(input_file)
    cleaned_entries = clean_data(entries)
    save_data(cleaned_entries, output_file)

    print("Loaded entries:", len(entries))
    print("Saved cleaned entries:", len(cleaned_entries))
    print("First cleaned entry:", cleaned_entries[0] if cleaned_entries else None)
    return cleaned_entries


if __name__ == "__main__":
    run_clean()
