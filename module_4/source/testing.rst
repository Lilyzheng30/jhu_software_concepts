Testing Guide
=============

Markers
-------

All tests are marked with one or more of:

- ``web``: page load / HTML structure
- ``buttons``: button endpoints & busy-state behavior
- ``analysis``: formatting/rounding of analysis output
- ``db``: database schema/inserts/selects
- ``integration``: end-to-end flows

Run All Tests
-------------

.. code-block:: bash

   pytest -c module_4/pytest.ini -m "web or buttons or analysis or db or integration"

Selectors
---------

The current HTML asserts against button text such as "Pull Data" and
"Update Analysis".

Test Doubles
------------

Tests use monkeypatching to avoid live network calls and to control scraper
outputs for deterministic coverage.

