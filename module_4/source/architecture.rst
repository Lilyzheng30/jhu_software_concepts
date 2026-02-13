Architecture
============

Web Layer (Flask)
-----------------

- ``module_4/src/app.py`` provides the Flask application.
- The Analysis page renders database metrics and exposes Pull Data / Update Analysis actions.

ETL Layer
---------

- ``module_4/src/module_2/scrape.py`` downloads raw entries.
- ``module_4/src/module_2/clean.py`` normalizes fields.
- ``module_4/src/load_data.py`` loads rows into PostgreSQL with idempotent inserts.

Database Layer
--------------

- PostgreSQL stores applicants in the ``applicants`` table.
- ``module_4/src/query_data.py`` contains SQL used by the analysis page.

