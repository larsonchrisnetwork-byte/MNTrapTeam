# MNTrapTeam 4.4.1

Fixes the Recent Score Scout hanging on slow ShootScoreBoard pages.

Changes:
- prints startup and discovery progress;
- 4-second timeout for shoot-ID discovery pages;
- 5-second timeout while loading each recent shoot;
- prints every recent shoot being scanned;
- skips slow/bad pages and continues;
- still requires no browser login.

Run:
    & ".\.venv\Scripts\python.exe" -m mntrapteam.recent_score_scout_cli preview

For a narrower first test:
    --id-scan 2050:2125
