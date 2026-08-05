# Architecture

`database.py` owns SQLite persistence. `importers.py` normalizes external tables and updates scores/statistics. `rules.py` implements MTA requirements. `calculations.py` ranks shooters and projects averages. `services.py` handles exports, snapshots, and browser handoff. `gui.py` is a PySide6 desktop shell.
