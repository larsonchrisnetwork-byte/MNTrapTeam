# MNTrapTeam 2.8.0 — Secure Connector Foundation

Provides separate persistent local browser sessions for:

- SOS Clays
- MyATA / ShootATA
- ATA Scores

Passwords are never requested or stored by MNTrapTeam. Login happens directly
inside the provider's website. Browser cookies and session storage remain only
under:

    data/browser_sessions/

That directory is excluded from Git.

## Apply

```powershell
cd H:\MNTrapTeam\MNTrapTeam
& ".\.venv\Scripts\python.exe" .\Apply_v2.8.0.py
.\Install_MNTrapTeam.bat
& ".\.venv\Scripts\python.exe" -m playwright install chromium
& ".\.venv\Scripts\python.exe" -m pytest -q tests
```

## Connect accounts

```powershell
& ".\.venv\Scripts\python.exe" -m mntrapteam.connector_cli connect sos
& ".\.venv\Scripts\python.exe" -m mntrapteam.connector_cli connect shootata
```

For each command, a browser opens. Sign in on the provider's website, return to
PowerShell, and press Enter. MNTrapTeam saves only the browser session.

ATA Scores is presently public:

```powershell
& ".\.venv\Scripts\python.exe" -m mntrapteam.connector_cli check ata_scores
```

## Check or clear sessions

```powershell
& ".\.venv\Scripts\python.exe" -m mntrapteam.connector_cli status
& ".\.venv\Scripts\python.exe" -m mntrapteam.connector_cli check sos
& ".\.venv\Scripts\python.exe" -m mntrapteam.connector_cli check shootata
& ".\.venv\Scripts\python.exe" -m mntrapteam.connector_cli clear sos
```

This release creates the secure session layer. Provider-specific score
extraction comes next, after observing the pages available inside the user's
legitimate authenticated sessions.
