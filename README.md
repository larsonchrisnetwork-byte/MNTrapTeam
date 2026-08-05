# MNTrapTeam

A Windows desktop application for tracking Minnesota ATA shooters, importing ShootScoreBoard high-gun reports, reconciling official ShootATA data, checking Minnesota Trapshooting Association State Team eligibility, projecting averages, calculating teams, and preserving historical seasons.

## Highlights

- Modern PySide6 desktop GUI with dashboard, shooters, imports, standings, projections, archives, and settings.
- SQLite database with automatic schema creation and migrations.
- CSV, XLSX, HTML, and PDF import support for ShootScoreBoard-style reports.
- Official-data reconciliation workflow for ShootATA exports and browser-assisted downloads.
- MTA rules engine based on the October 2024 State Team Requirements sheet.
- Minnesota target, club, HAA, category, and total-target eligibility checks.
- HOA rankings and automatic Men, Lady, Vet, Sr Vet, Junior, and Sub-Junior teams.
- Scenario projections and historical season snapshots.
- CSV/XLSX/PDF reports and database backup/restore.
- Unit tests and sample data.

## Windows quick start

1. Install Python 3.11 or newer from python.org and select **Add Python to PATH**.
2. Double-click `Install_MNTrapTeam.bat` once.
3. Double-click `Run_MNTrapTeam.bat`.

The first launch creates `data/mntrapteam.db` and loads sample data only when requested from the GUI.

## ShootATA security

MNTrapTeam does not store your ShootATA password in the database. The recommended workflow is to log in with your normal browser, export or save the official shooter information, and import it. An optional browser-assisted connector opens the official login page but does not bypass authentication or CAPTCHA.

## GitHub

This folder is initialized as a local Git repository. To publish it:

```powershell
gh repo create MNTrapTeam --private --source . --remote origin --push
```

or create an empty repository on GitHub and follow the displayed `git remote add` / `git push` commands.

## Disclaimer

ShootScoreBoard states that its scores are not official. Use ShootATA or MTA records for official decisions. Always confirm final State Team selections with the MTA.
