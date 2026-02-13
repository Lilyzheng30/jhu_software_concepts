Lily Zheng  
JHED: lzheng45  
Module 4 Assignment: Pytest + Sphinx Docs  

Grad Cafe Analytics (Module 4)

File Overview (Module 4)
- tests/: pytest suite (all tests marked: web, buttons, analysis, db, integration)
- pytest.ini: pytest config + coverage settings
- coverage_summary.txt: terminal output from the 100% coverage run
- actions_success.png: screenshot of a successful GitHub Actions run
- docs/: Sphinx project
  - docs/source/: conf.py, index.rst, overview.rst, architecture.rst, testing.rst, api.rst
  - docs/build/html/: generated HTML output from `make html`
- venv/: local virtual environment (not required to submit)

How to Run Tests
- From repo root:
  pytest -c module_4/pytest.ini -m "web or buttons or analysis or db or integration"

Sphinx Docs
- Build HTML from module_4/docs:
  make html
- Read the Docs config: .readthedocs.yaml (repo root)
- RTD URL: <PASTE YOUR READTHEDOCS LINK HERE>
