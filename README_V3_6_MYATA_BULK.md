# MNTrapTeam 3.6.0 — Bulk MyATA Rendered Baselines

The rendered MyATA Search/Buddies UI provides both:

- Shooter Yearly Summary
- 2026 Score Details

The importer uses Score Details to sum exact **targets shot at** and **hits**,
then checks those target totals against the yearly summary before writing.

For the captured Aiden Weber example it parses:

- Singles: 1000 shot / 911 hit = 91.10%
- Handicap: 800 shot / 687 hit = 85.88%
- Doubles: 400 shot / 268 hit = 67.00%

Start with a five-shooter dry run:

    & ".\.venv\Scripts\python.exe" -m mntrapteam.myata_bulk_dom_cli `
      --season 2026 --limit 5 --dry-run

If the Search/Buddies automation works for those five, rerun without
`--dry-run`, then increase the limit.

The scraper never converts hit percentage into target counts. It reads exact
Shot and Hit columns from MyATA Score Details.
