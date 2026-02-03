Lily Zheng
JHED: lzheng45
Module_2 Assignment: Web Scraping
Due 2/1/2026 11:59pm

robots.txt was checked and it stated: User-agent: *; Content-Signal: search=yes, ai-train=no; Allow: /. The /survey/ path is not disallowed.

Approach
- I scraped The Grad Cafe survey pages by looping over page numbers and downloading each HTML page with urllib. I parsed the listing table using BeautifulSoup.
- Each applicant entry is represented as a dictionary. I store raw fields first (program_raw, university_raw, applicant_status_raw, date_added_raw, semester_year_start_raw, etc.).
- The Grad Cafe listing uses a “main row” plus an optional “meta row” underneath it. The meta row contains term (e.g., Fall 2026) and sometimes citizenship. The scraper checks the next row for keywords like fall/spring/summer/winter or international/american to decide whether it is a meta row, then parses both rows together.
- If a row has a detail-page link, I visit that page and extract extra fields (program, degree type, nationality, GRE scores, GPA) from the detail <dl> and <ul> sections.
- After scraping, I save the raw list to applicant_data.json.
- In clean.py I load applicant_data.json, rename keys to cleaner names, normalize whitespace, and convert placeholder zero GRE/GPA values to None. I also parse applicant_status into acceptance_date or rejection_date while keeping the original status.
- The cleaned output is written to out.json for downstream use.
- LLM step: llm_hosting/app.py can standardize program and university names by combining program + university text, then using a tiny local LLM plus canonical lists. It outputs JSONL for easier streaming. I edited it a bit to make sure that it did not print empty values and also corrected some of the school outputs to make them standarized. 

scrape.py
- scrape_data() pulls data from The Grad Cafe using BeautifulSoup and urllib. It also extracts the semester/year shown on the main page.
- parse_row() extracts the main-row fields (program, university, status, date, and the detail-page URL). Each page shows 20 applicants.
- parse_detail_page() extracts fields from each applicant detail page (e.g., nationality and GRE scores).
- save_data() writes the raw results to applicant_data.json.

clean.py
- load_data() loads applicant_data.json for processing.
- clean_data() normalizes whitespace, combines program + university, and keeps numeric GRE/GPA values only when they are non-zero.
- save_data() writes the cleaned output to out.json.

LLM standardization (llm_hosting)
- The LLM app can further standardize program/university names and output JSONL.
- I edited the LLM by adding 2 functions: _build_program_text() combines program + university before sending to the LLM, and _fallback_university() replaces placeholder outputs (e.g., "Unknown" or "University of X") with the input university.
- python3 app.py --file "../llm_extend_applicant_data.json" > "../out.json" -- was used to run the file but the information was saved into the jsonl.
- I then ran jq -s . llm_extend_applicant_data.json.jsonl > out.json -- to put my values into a json file called out.json.

Known Bugs
- None. If the LLM returns placeholders like "University of X" or "Unknown", I added a fallback to use the input university, but the LLM can still sometimes title-case acronyms (e.g., "UNC" -> "Unc"). A future fix would be to extend the canonical university list or add more abbreviation rules.

NOTE!! on model files
When I attempted adding everything to my github file, it stated that the file was too large (i believe it was refering to the file in the LLM /jhu_software_concepts/module_2/llm_hosting/models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf) so I had to not include that in my submission. I hope that is fine, if not I can try to find a way to submit it by other means. 
This meant that the Large LLM model files (.gguf) wasnt not included in this repository due to GitHub file size limits. The model is downloaded automatically on first run or can be specified via the MODEL_FILE environment variable.
