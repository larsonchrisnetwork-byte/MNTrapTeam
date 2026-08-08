# MNTrapTeam 3.4.1 — Fast Zone Discovery

Replaces the slow `shootid=2000..2100` brute-force scan.

The new discovery:

1. downloads ShootScoreBoard's homepage,
2. finds the site's own year-selection form,
3. submits the 2026 option using the site's actual field names,
4. parses the returned shoot listing,
5. matches:
   - Southern Zone / Lester Prairie
   - Central Zone / Beaverbrook
   - Northern Zone / Grand Rapids

Run:

```powershell
& ".\.venv\Scripts\python.exe" -m mntrapteam.scoreboard_listing_cli --year 2026
```

This should require only the homepage plus one year-listing request instead of
100+ shoot page requests.
