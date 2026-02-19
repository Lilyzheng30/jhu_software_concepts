Lily Zheng  
JHED: lzheng45  
Module 5 Assignment: Software Assurance + Secure SQL (SQLi Defense) Assignment 

Grad Cafe Analytics (Module 4)

File Overview (Module 4)
- tests/: pytest suite (all tests marked: web, buttons, analysis, db, integration)
    - test_flask_page.py: checks the flask app factory exist, required route exist, and get /analysis returns the page with analysis, pull data and update analysis
    - test_buttons.py: verifies that the api endpoints return 200 when not busy and 409 when busy 
    - test_analysis_format.py: ensure the rendered analysis includes anwer labels and that percentages are fromated with 2 decimals
    - test_db_insert.py: uses run_load() to insert test rows in Postgres and verifies required fields exist
    - test_integration_end_to_end.py: checks if the low is correct from the LLM pull data to the update analysis and finally to the get analysis
    - test_clean_module.py: covers clean.py functions
    - test_scrape_module.py: covers scrape.py parsing and scraping logic with mocked HTML
    - test_query_data.py: covers query_data.py helper functions and __main__ path with mocked DB connection
    - test_llm_hostin_app.py: coveres the LLM standardization module app.py using mock LLM and ensures normalization paths and CLI are covered without running real model by using a mock
- pytest.ini: pytest config + coverage settings
- coverage_summary.txt: terminal output from the 100% coverage run
- actions_success.png: screenshot of a successful GitHub Actions run
- docs/: Sphinx project
  - docs/source/: conf.py, index.rst, overview.rst, architecture.rst, testing.rst
    - conf.py: sphinx configuration sets project information, extensions and python path so that autodoc can import code
    - index.rst: main landing page for doc with the table of context and the autodoc sections
    - overview.rst: how to run page, setup, running the app, DB information, enviroment vars, and how to run tests
    - architecture.rst: describes the system structure, web flask, ETL pipeline, DB
    - testing.rst: Explains pytest markers, how to run the test suite and any test doubling
  - docs/build/html/: generated HTML output from `make html`
- src/: module_3 files
- build/html/: html files for the document page with each page having a different html file 
- .github/workflows/tests.yml (repo root): GitHub Actions workflow (must be at repo root to run).
- .readthedocs.yaml (repo root): Read the Docs build configuration (must be at repo root to run).


How to Run Tests
- From repo root:
  # Full test suite (uses loader setup SQL such as CREATE TABLE/INDEX).
  # Use an admin-capable DB user for test execution.
  unset DB_HOST DB_PORT DB_NAME DB_USER DB_PASSWORD
  export DATABASE_URL="postgresql://postgres:replace_me@127.0.0.1:5432/sm_app"
  pytest -c module_5/pytest.ini module_5/tests -m "web or buttons or analysis or db or integration" --cov=module_5/src


How to Run the App
- From module_5/src:
  # Runtime least-privilege app account (recommended for normal app execution).
  export DB_HOST="127.0.0.1"
  export DB_PORT="5432"
  export DB_NAME="sm_app"
  export DB_USER="sm_app_user"
  export DB_PASSWORD="replace_me"
  python app.py

Least-Privilege Runtime vs Full Test Runs
- Full tests in this project call loader/bootstrap logic that creates tables/indexes, so tests should run with an admin-capable account via `DATABASE_URL`.
- Normal app runtime should use the least-privilege account (`sm_app_user`) through `DB_*` environment variables.

Sphinx Docs
- Build HTML from module_4/docs:
  make html
- Read the Docs config: .readthedocs.yaml (repo root)
- RTD URL: (https://app.readthedocs.org/projects/jhu-software-concepts-lilyz/)

Pylint (Module 5)
- Install Pylint:
   python3 -m pip install pylint
- Run Pylint on Python files in `module_5/src`:
  PYLINTHOME=/tmp/pylint pylint --rcfile module_5/.pylintrc \
$(find module_5/src -type f -name "*.py" -not -path "*/__pycache__/*")



Python Dependency Graph (pydeps + Graphviz)
- Install tools:
  - `pip install pydeps`
  - `brew install graphviz`
  - Verify Graphviz is available: `dot -V`
- Generate SVG (from `module_5`):
  - `cd src`
  - `pydeps app.py --noshow -T svg -o ../dependency.svg`
  - Output file is saved at `module_5/dependency.svg`

Dependency Graph Summary
- The dependency graph centers on `app.py`, which coordinates the web routes and the data pipeline flow.
- `app.py` depends on `query_data.py` for SQL analytics reads and on `load_data.py` for writing normalized rows into PostgreSQL.
- The pipeline path calls `module_2.scrape` to collect raw GradCafe rows and `module_2.clean` to normalize extracted fields before loading.
- LLM standardization is integrated through `module_2.llm_hosting.app`, which enriches records with standardized program and university names.
- Database connectivity is provided by `psycopg`, while request routing and templating are handled by `Flask`.
- Scraping and parsing rely on `bs4` (BeautifulSoup), and the local LLM stack uses `huggingface_hub` and `llama-cpp-python`.

Fresh Install (pip + uv)
- pip method (clean environment):
  - `python3 -m venv module_5/venv`
  - `source module_5/venv/bin/activate`
  - `pip install -r module_5/requirements.txt`
  - `pip install -e module_5`
- uv method (clean environment):
  - `uv venv module_5/.venv`
  - `source module_5/.venv/bin/activate`
  - `uv pip sync module_5/requirements.txt`
  - `uv pip install -e module_5`
- Why setup.py packaging helps:
  - `pip install -e module_5` gives consistent import resolution between local runs, tests, and CI.
  - Editable installs reduce path-related issues and support reproducible environment setup.

Database Hardening (Least Privilege)
- App code reads DB settings from environment variables:
  `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- Optional compatibility fallback:
  `DATABASE_URL`
- Optional admin-only bootstrap vars (for one-time DB creation in loader):
  `DB_ADMIN_HOST`, `DB_ADMIN_PORT`, `DB_ADMIN_NAME`, `DB_ADMIN_USER`, `DB_ADMIN_PASSWORD`

Suggested least-privilege SQL setup
```sql
CREATE ROLE sm_app_user LOGIN PASSWORD 'replace_me' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
GRANT CONNECT ON DATABASE sm_app TO sm_app_user;
GRANT USAGE ON SCHEMA public TO sm_app_user;
GRANT SELECT, INSERT ON TABLE applicants TO sm_app_user;
```

Why these permissions
- `SELECT` is needed for analysis/read endpoints.
- `INSERT` is needed for `run_load()` when loading new rows.
- No `DROP`, `ALTER`, ownership, or superuser privileges are granted.

- Latest result:
  PYLINTHOME=/tmp/pylint pylint --rcfile module_5/.pylintrc \
  $(find module_5/src -type f -name "*.py" -not -path "*/__pycache__/*")
