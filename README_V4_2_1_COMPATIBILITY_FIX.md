# MNTrapTeam 4.2.1

Fixes the pytest collection failure introduced in v4.2.0.

Changes:
- restores `_hoa_from_disciplines()` for backward compatibility with the
  existing test suite;
- keeps `_hoa()` as a wrapper around that established helper;
- installer verifies the installed MyATA CLI actually exposes `--ata-file`;
- keeps the v4.2 Men's Team Race / official-vs-current design intact.

After applying:
    & ".\.venv\Scripts\python.exe" .\Apply_v4.2.1.py
    & ".\.venv\Scripts\python.exe" -m pytest -q tests
    & ".\.venv\Scripts\python.exe" -m mntrapteam.myata_bulk_dom_cli --help
