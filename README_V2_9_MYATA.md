# MNTrapTeam 2.9.0 — MyATA Official Capture

Uses the saved authenticated MyATA browser profile to open Shooter Information
Center, click My Scores, capture tables and same-domain JSON responses, and
import recognizable official target-year totals.

No password or cookie is written to the capture directory. Connector captures
remain under the Git-ignored path:

    data/connector_downloads/myata/

## Apply

```powershell
cd H:\MNTrapTeam\MNTrapTeam
& ".\.venv\Scripts\python.exe" .\Apply_v2.9.0.py
& ".\.venv\Scripts\python.exe" -m pytest -q tests
```

Ensure `user_ata_number` is set in Settings, then run:

```powershell
& ".\.venv\Scripts\python.exe" -m mntrapteam.myata_cli --season 2026
```

Use `--headed` to watch the browser if MyATA navigation needs visual review:

```powershell
& ".\.venv\Scripts\python.exe" -m mntrapteam.myata_cli --season 2026 --headed
```

If totals are not recognized, the command still saves:

- `page_meta.json`
- `page_text.txt`
- `tables.json`
- `network_json.json`

Those local sanitized captures let the parser be adapted to the exact MyATA
page without exposing passwords or session cookies.
