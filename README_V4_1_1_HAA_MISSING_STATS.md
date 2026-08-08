# MNTrapTeam 4.1.1

Targets the only two eligibility-critical missing 2026 season-stat records:

- Anna M Berger — ATA 2216215
- Tucker L Fredrickson — ATA 2306892

First run:

    & ".\.venv\Scripts\python.exe" -m mntrapteam.haa_missing_stats_targets_cli

This verifies whether each still lacks 2026 season_stats and writes:

    data/connector_downloads/myata_targeted_haa_missing_stats.csv

The next patch adds explicit --ata-file support to the existing MyATA bulk importer
so these two can be imported directly without disturbing the 143-shooter baseline.
