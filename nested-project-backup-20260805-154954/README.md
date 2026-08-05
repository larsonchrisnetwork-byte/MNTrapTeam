# MNTrapTeam 1.1

Windows desktop and command-line application for tracking Minnesota ATA shooters, importing ShootScoreBoard reports, reconciling authorized ShootATA exports, checking MTA State Team eligibility, calculating teams, projecting averages, exporting reports, and archiving seasons.

## Verified MTA rules
The included `docs/MTA-State-Team-Requirements-10_24.pdf` is the source for the rules file. Men: 1,500 singles, 1,200 handicap, 1,000 doubles. General in-state minimums: 700 singles, 700 handicap, 400 doubles; HAA and four-club rules apply with the stated junior exemptions.

## Install and run
1. Install Python 3.11+ and select **Add Python to PATH**.
2. Double-click `Install_MNTrapTeam.bat`.
3. Double-click `Run_MNTrapTeam.bat`.

## Data safety
The program does not store a ShootATA password or bypass login/CAPTCHA. Use the browser login and import an export you are authorized to access. ShootScoreBoard imports remain marked unofficial until reconciled. Never commit `data/`, exports, credentials, cookies, or browser profiles.

## Command line
After installation:
```powershell
python -m mntrapteam.cli rank --season 2026 --team MEN
python -m mntrapteam.cli import-official samples\official_shootata_import.csv --season 2026
python -m mntrapteam.cli export --season 2026 --format xlsx
```

## Tests
```powershell
python -m pytest -q
```

## Publish changes
```powershell
git add .
git commit -m "Complete MNTrapTeam 1.1"
git push
```
