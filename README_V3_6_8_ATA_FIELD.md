# MNTrapTeam 3.6.8 — ATA Field Priority

v3.6.7 successfully completed two full MyATA Search/Buddies dry-run lookups.

Observed behavior:
- the scraper first tried Last Name,
- erased the ATA number,
- tried First Name,
- erased it,
- finally reached ATA Number,
- then correctly selected the shooter and parsed 2026 totals.

v3.6.8 keeps the working fallback behavior but ranks Search/Buddies inputs so
the field whose label/metadata contains `ATA Number` is attempted first.

Recommended next test:

    & ".\.venv\Scripts\python.exe" -m mntrapteam.myata_bulk_dom_cli `
      --season 2026 `
      --limit 5 `
      --dry-run `
      --manual-assist

If five shooters succeed, rerun without `--dry-run`.
