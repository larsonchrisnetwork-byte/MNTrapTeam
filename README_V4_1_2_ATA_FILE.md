# MNTrapTeam 4.1.2

Adds `--ata-file` to `mntrapteam.myata_bulk_dom_cli`.

Expected CSV:
    ata_number,display_name

Example:
    & ".\.venv\Scripts\python.exe" -m mntrapteam.myata_bulk_dom_cli `
      --season 2026 `
      --ata-file ".\data\connector_downloads\myata_targeted_haa_missing_stats.csv" `
      --manual-assist

When `--ata-file` is provided, only those ATA numbers are processed, in file order.
