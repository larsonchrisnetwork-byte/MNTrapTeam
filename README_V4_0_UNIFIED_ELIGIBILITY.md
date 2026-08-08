# MNTrapTeam 4.0.0 — Unified Men's Open Eligibility Engine

This is the first permanent eligibility engine.

Current Men's Open rules implemented:
- HAA gate: State HAA OR verified HAA at the shooter's home Zone
- Total targets: 1500 Singles, 1200 Handicap, 100 Doubles
- Minnesota targets: 700 Singles, 700 Handicap, 700 Doubles
- Minnesota clubs: 4

The engine intentionally separates:
- HAA gate
- total-target minimums
- Minnesota in-state minimums
- 4-club requirement

New audit:
    & ".\.venv\Scripts\python.exe" -m mntrapteam.eligibility_audit_cli

This is the core to wire into the Live Team screen next.
