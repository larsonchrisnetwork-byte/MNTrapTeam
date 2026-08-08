# MNTrapTeam 3.7.0 — Minnesota Eligibility Enrichment

MyATA official baselines correctly populated total season targets/hits, but did
not populate:

- mn_singles_targets
- mn_handicap_targets
- mn_doubles_targets
- mn_clubs

The eligibility engine therefore showed most shooters red and `0/4 clubs`.

This release reuses MyATA 2026 Score Details and the previously captured SOS
club directory. The SOS club list includes each club's `stateProvince`, allowing
MyATA club-name rows to be classified as Minnesota or out of state.

Only the four Minnesota eligibility fields are updated. Official total
targets/hits are not changed.

Start with a five-shooter dry run:

    & ".\.venv\Scripts\python.exe" -m mntrapteam.myata_mn_enrich_cli `
      --season 2026 `
      --limit 5 `
      --dry-run `
      --manual-assist

Review the MN target totals, MN clubs, and any unmatched club names before
running without `--dry-run`.
