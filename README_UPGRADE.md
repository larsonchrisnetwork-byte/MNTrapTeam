# MNTrapTeam 1.7.0

Adds a safer data-ingestion pipeline:

- Official ShootATA imports are hashed and written to import history.
- Identical official files are blocked from being imported twice.
- A folder importer discovers CSV, Excel, HTML, and PDF files.
- Files are classified as official totals, ShootScoreBoard reports, or unknown.
- Each file reports rows read/imported, warnings, duplicate status, and errors.

Apply:

    & ".\.venv\Scripts\python.exe" .\Apply_v1.7.0.py
    & ".\.venv\Scripts\python.exe" -m pytest -q tests
