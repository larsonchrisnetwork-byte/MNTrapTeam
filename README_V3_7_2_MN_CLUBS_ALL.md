# MNTrapTeam 3.7.2

Fixes two Minnesota clubs found during the first production enrichment batch:

- Owatonna Gun Club
- Minneapolis Gun Club

Also changes `myata_mn_enrich_cli --limit` default from 25 to `None`.

Therefore:

- `--limit 25` = process 25
- no `--limit` = process all eligible shooters

Because earlier enrichment batches may have undercounted these clubs, rerun
with `--refresh` after applying:

    & ".\.venv\Scripts\python.exe" -m mntrapteam.myata_mn_enrich_cli `
      --season 2026 `
      --refresh `
      --manual-assist

This recalculates the Minnesota-only fields for the full HAA-qualified pool.
Official total MyATA targets/hits remain unchanged.
