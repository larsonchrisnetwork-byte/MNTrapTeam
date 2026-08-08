# MNTrapTeam 3.5.2 — SOS State HAA Import

The captured 2026 MN State Shoot HAA report provides enough information to
verify HAA completion without inventing per-event scores.

The importer validates that SOS `eventsData` contains exactly three HAA events:

- 200 Singles
- 100 Doubles
- 100 Handicap

Total: 400 targets shot at.

Because the user explicitly opened the SOS HAA report, a Minnesota shooter with
`eventsCompleted == 3` in `sortedReportData` is recorded as completing the
State HAA route.

`totalScore` is NOT used to infer Singles/Handicap/Doubles hits or season
targets. Those totals will come from event-level sources.

Run:

    & ".\.venv\Scripts\python.exe" -m mntrapteam.sos_state_haa_cli

This writes only State HAA qualification records.
