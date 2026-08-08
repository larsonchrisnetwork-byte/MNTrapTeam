# MNTrapTeam 4.2.0 — Men's Team Race

Purpose
-------
Show the race as it looks today with two separate data layers:

1. MyATA official totals / HOA.
2. Newer unofficial scores from imported score sites, added only when their
   event date is later than the newest event already present in the MyATA
   Score Details baseline.

The race table keeps qualified and not-yet-qualified Men's shooters together,
sorted by Current HOA, and shows exactly what each shooter still needs.

Key columns
-----------
- Race Rank
- Qualified Rank
- Current HOA
- MyATA HOA
- Current - MyATA
- Current cut
- HAA
- current total targets
- Minnesota target counts
- Minnesota clubs
- What They Need
- Pending Targets
- MyATA Through
- Newest Unofficial
- Data Source

Safety against double counting
------------------------------
A provisional score is not added until MNTrapTeam knows the shooter's
MyATA official-through date. Refreshing MyATA records this date from the
rendered Score Details table.

Targeted MyATA refresh
----------------------
The existing `--ata-file` flow is now supported.

Example:

    & ".\.venv\Scripts\python.exe" -m mntrapteam.myata_bulk_dom_cli `
      --season 2026 `
      --ata-file ".\data\connector_downloads\myata_targeted_haa_missing_stats.csv" `
      --manual-assist `
      --refresh

Recent Minnesota ShootScoreBoard shoot
---------------------------------------
Import normally; it counts for current HOA, total targets and MN targets.

Recent out-of-state ShootScoreBoard shoot (Grand American, etc.)
-----------------------------------------------------------------
Use:

    & ".\.venv\Scripts\python.exe" -m mntrapteam.live_import SHOOT_ID `
      --season 2026 `
      --club "World Shooting & Recreational Complex" `
      --out-of-state

Those targets affect Current HOA and total targets but do not count toward the
Minnesota 700/700/700 minimum.

CLI race preview
----------------

    & ".\.venv\Scripts\python.exe" -m mntrapteam.mens_race_cli

Then launch the normal GUI and open Live Team Race.

HAA refresh pool
----------------
The MyATA bulk candidate pool now includes both verified State HAA and verified
home-Zone HAA shooters. Zone-only qualifiers are therefore eligible for
targeted official refreshes.
