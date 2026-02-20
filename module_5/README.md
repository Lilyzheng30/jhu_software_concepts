Lily Zheng  
JHED: lzheng45  
Module 5 Assignment: Software Assurance + Secure SQL (SQLi Defense) Assignment 

Software Assurance + Secure SQL (Module 5)

File Overview (Module 5)
- tests/: pytest suite (all tests marked: web, buttons, analysis, db, integration)
    - test_flask_page.py: checks the flask app factory exist, required route exist, and get /analysis returns the page with analysis, pull data and update analysis
    - test_buttons.py: verifies that the api endpoints return 200 when not busy and 409 when busy 
    - test_analysis_format.py: ensure the rendered analysis includes anwer labels and that percentages are fromated with 2 decimals
    - test_db_insert.py: uses run_load() to insert test rows in Postgres and verifies required fields exist
    - test_integration_end_to_end.py: checks if the low is correct from the LLM pull data to the update analysis and finally to the get analysis
    - test_clean_module.py: covers clean.py functions
    - test_scrape_module.py: covers scrape.py parsing and scraping logic with mocked HTML
    - test_query_data.py: covers query_data.py helper functions and __main__ path with mocked DB connection
    - test_llm_hosting_app.py: coveres the LLM standardization module app.py using mock LLM and ensures normalization paths and CLI are covered without running 
    - test_app_pipeline.py: pipeline flow tests
    - test_sql_injection_defense.py: SQL injection defense tests
    - test_load_and_app_utils.py: utility/env/connection tests
    real model by using a mock
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
  - docs/build/html/: generated HTML output from make html
- src/: module_3 files
- build/html/: html files for the document page with each page having a different html file 
- data_builders.py: helper module used by app/tests
- db_config.py: env-based DB connection helpers
- CI_run.png : CI proof screenshot
- snyk_analysis.png: Snyk dependency scan evidence
- SAST.png: snyk code test evidence
- setup.py: packaging/install metadata
- module_5/.pylintrc: pylint rules used for 10/10 score
- dependency.svg: pydeps output graph
- .env.example: env var template
- .github/workflows/ci.yml (repo root): GitHub Actions workflow (must be at repo root to run).
- .readthedocs.yaml (repo root): Read the Docs build configuration (must be at repo root to run).



How to Run Tests
- From repo root:
  - Full test suite (uses loader setup SQL such as CREATE TABLE/INDEX).
  - Use an admin-capable DB user for test execution.
  
unset DB_HOST DB_PORT DB_NAME DB_USER DB_PASSWORD
export DATABASE_URL="postgresql://postgres:replace_me@127.0.0.1:5432/sm_app"
pytest -c pytest.ini tests -m "web or buttons or analysis or db or integration" --cov=src



How to Run the App
- source venv/bin/activate
- export DATABASE_URL="postgresql://postgres:abc123@127.0.0.1:5432/sm_app"
- unset DB_HOST DB_PORT DB_NAME DB_USER DB_PASSWORD
- cd src
- python3 app.py

Least-privilege SQL setup
- CREATE ROLE sm_app_user
- LOGIN PASSWORD 'ABC123'
- NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
- GRANT CONNECT ON DATABASE sm_app TO sm_app_user;
- GRANT USAGE ON SCHEMA public TO sm_app_user;
- GRANT SELECT, INSERT ON TABLE applicants TO sm_app_user;

Least-Privilege Runtime vs Full Test Runs
- Full tests in this project call loader/bootstrap logic that creates tables/indexes, so tests should run with an admin-capable account via DATABASE_URL
- Normal app runtime should use the least-privilege account (sm_app_user) through DB_* environment variables.

Sphinx Docs
- Build HTML from module_4/docs:
  make html
- Read the Docs config: .readthedocs.yaml (repo root)
- RTD URL: (https://app.readthedocs.org/projects/jhu-software-concepts-lilyz/)

Pylint (Module 5)
- Install Pylint:
   python3 -m pip install pylint
- Run Pylint on Python files in module_5:
PYLINTHOME=/tmp/pylint pylint --rcfile .pylintrc \
$(find src -type f -name "*.py" -not -path "*/__pycache__/*")

Python Dependency Graph (pydeps + Graphviz)
- Install tools:
  - pip install pydeps
  - brew install graphviz
  - Verify Graphviz is available: dot -V
- Generate SVG (from module_5):
  - cd src
  - pydeps app.py --noshow -T svg -o ../dependency.svg
  - Output file is saved at module_5/dependency.svg

Dependency Graph Summary
- The dependency graph shows a visual representation of the different parts of a project, such as modules, libraries, or packages, relying on one another. 
- The various dependencies are in module_5/requirements.txt and the main layer, app.py is calling on query_data.py and load_data.py 
  - Which is used to load the data and includes the sql query. 
- The data is obtained from the module_2 files which include scrape.py and clean.py which obtain data from the website https://www.thegradcafe.com/. 
- The data is then handled by the LLM in llm_hosting/app.py. All of these connections are seen with the dependency graph. 
- The various supporting dependencies in requirements.txt include the runtime libraries such as 
  - flask, psycopg and the quality/security tools such as pytest, pytest-cov, pylint, pydeps, snyk. 
-Overall, the graph helps to show a layered architecture of the entrypoint, the data/query pipeline and the external data/model services.
- Database connectivity is provided by psycopg, while request routing and templating are handled by Flask.
- Scraping and parsing rely on bs4 (BeautifulSoup), and the local LLM stack uses huggingface_hub and llama-cpp-python.

How to Install/Run via pip and uv
pip
- python3 -m venv venv
- source venv/bin/activate
- pip install -r requirements.txt
- pip install -e .
uv
- uv venv .venv
- source .venv/bin/activate
- uv pip sync requirements.txt
- uv pip install -e .

Run test
- unset DB_HOST DB_PORT DB_NAME DB_USER DB_PASSWORD`
- export DATABASE_URL="postgresql://postgres:replace_me@127.0.0.1:5432/sm_app"
- pytest -c pytest.ini tests -m "web or buttons or analysis or db or integration" --cov=src

Run app
- unset DB_HOST DB_PORT DB_NAME DB_USER DB_PASSWORD
- export DATABASE_URL="postgresql://postgres:replace_me@127.0.0.1:5432/sm_app"
- cd src
- python3 app.py

- Why setup.py packaging helps:
  - Packaging matters because it makes the project installable in a standard Python way, so imports work the same in local runs, tests, and CI. 
  - With setup.py, I can run pip install -e . inside module_5

Database Hardening (Least Privilege)
- App code reads DB settings from environment variables:
  `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- Optional compatibility fallback:
  `DATABASE_URL`
- Optional admin-only bootstrap vars (for one-time DB creation in loader):
  `DB_ADMIN_HOST`, `DB_ADMIN_PORT`, `DB_ADMIN_NAME`, `DB_ADMIN_USER`, `DB_ADMIN_PASSWORD`

