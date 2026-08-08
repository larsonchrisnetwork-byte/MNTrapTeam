# MNTrapTeam 3.6.9 — Resume + Logged-In User

The first real 25-shooter batch imported 24 official MyATA baselines.

Only the logged-in shooter failed, because MyATA treats the user's own record
differently from Search/Buddies results.

v3.6.9 adds:

- automatic skipping of shooters already sourced from
  `MyATA official rendered detail`;
- `--refresh` if you intentionally want to re-import them;
- special handling for the ATA number in `config/settings.json`:
  that shooter is read through the logged-in My Scores table instead of
  Search/Buddies.

Recommended next run:

    & ".\.venv\Scripts\python.exe" -m mntrapteam.myata_bulk_dom_cli `
      --season 2026 `
      --limit 25 `
      --manual-assist

Because already-imported shooters are skipped, this should move on to the next
missing official baselines rather than redoing the same 24.
