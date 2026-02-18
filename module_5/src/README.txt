Lily Zheng
JHED: lzheng45
Module_3 Assignment: Database Queries Assignment Experiment
Due 2/8/2026 11:59pm

Module 3 - Grad School Cafe Analysis Web App (Database Queries Assignment Experiment)

Website
- It loads applicant records, runs analysis queries, and shows answers on a web page.
- It also includes buttons:
  - Pull Data: scrape + clean + LLM + load into DB
  - Update Analysis: refresh analysis view when requested

Project Files
- app.py: Flask routes, Pull Data / Update Analysis button handlers, page rendering
- load_data.py: Creates tables/index and inserts JSON data into PostgreSQL
- query_data.py: SQL query bank and print output
- module_2_out.json: cumulative historical dataset used to initiate the DB
- out.json: latest batch created by Pull Data pipeline
- module_2/: copied Module 2 pipeline (scrape.py, clean.py, llm_hosting, etc.)

Database
- DB name: sm_app
- Table: applicants, URL uniqueness is enforced with a unique index and Duplicate URLs are ignored on insert (ON CONFLICT DO NOTHING)

Data initial load
- run_load() loads JSON into applicants and default input file is module_2_out.json

Pull Data button
- runs scrape.py to get newest rows, runs clean.py to normalize raw rows, runs llm_hosting/app.py to standardize program/university
- writes latest processed rows to out.json and merges new URLs from out.json into module_2_out.json
- reloads DB from module_2_out.json

Update Analysis button
- refreshes analysis output on the webpage and if Pull Data is currently running, update is blocked and user is notified

Notes:
- When running the codes, I created venv, pip install -r requirements.txt, Load DB (python3 load_data.py), Start web app (python3 app.py), open http://0.0.0.0:8080
- In terms of setting up PostgreSQL, I installed PostgreSQL onto my laptop and used these commands: brew services start postgresql@16, createuser -s postgres, psql -d postgres -c "ALTER USER postgres WITH PASSWORD 'abc123';"
- For testing my code, I made sure each time the database was reset, which I used these commands to drop the database and verify if it was dropped: psql -U postgres -d postgres -c "DROP DATABASE sm_app;", psql -U postgres -d sm_app -c "SELECT COUNT(*) AS total_rows FROM applicants;"
- For work flow, I did python3 load_data.py and python3 app.py and that was all I needed to have the website running
- For the website , Pull Data button is the long step that fetches/processes new data from the gradcafe website and inserts them into the database; after Pull Data finishes, clicking Update Analysis reruns the queries and reloads the page with updated results. Update Analysis is only available when Pull Data is not currently running.
- In terms of running the pull data, because it is processing the information through the LLM, the time it takes to pull data is long (5-10+ minutes).

Notes on LLM Model Files
- Large .gguf model files are not committed to GitHub due to file size limits. it is in .gitignore
- The model is downloaded on first run (or set with MODEL_FILE env var).


