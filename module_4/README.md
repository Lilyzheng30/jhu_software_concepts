Lily Zheng  
JHED: lzheng45  
Module 4 Assignment: Testing and Documentation Assignment

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
- .readthedocs.yaml (repo root): Read the Docs build configuration (Python version, Sphinx conf path, and requirements to install).


How to Run Tests
- From repo root:
  pytest -c module_4/pytest.ini -m "web or buttons or analysis or db or integration"

Sphinx Docs
- Build HTML from module_4/docs:
  make html
- Read the Docs config: .readthedocs.yaml (repo root)
- RTD URL: (https://app.readthedocs.org/projects/jhu-software-concepts-lilyz/)
