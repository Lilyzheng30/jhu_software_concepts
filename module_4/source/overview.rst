Overview & Setup
================

This project provides a Grad Cafe analytics application with:

- A Flask web UI that displays analysis and provides Pull Data / Update Analysis actions.
- An ETL pipeline that scrapes, cleans, and loads data into PostgreSQL.
- Query logic for summary analytics.

Run the App
-----------

From ``module_4/src``:

.. code-block:: bash

   python app.py

By default it connects to PostgreSQL at ``127.0.0.1:5432`` with database
``sm_app`` and user ``postgres`` (see ``module_4/src/app.py``).

Environment Variables
---------------------

The current implementation uses hardcoded DB settings in ``module_4/src/app.py``.
If you add ``DATABASE_URL`` support later, document it here.

Run Tests
---------

From the repo root:

.. code-block:: bash

   pytest -c module_4/pytest.ini -m "web or buttons or analysis or db or integration"

