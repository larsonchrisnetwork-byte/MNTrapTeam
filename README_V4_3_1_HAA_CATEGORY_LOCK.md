# MNTrapTeam 4.3.1 — HAA Hard Gate + Qualifying Category Lock

Preview first:
    & ".\.venv\Scripts\python.exe" -m mntrapteam.state_team_lock_cli preview

This does not change the database.

After reviewing the Men's pool:
    & ".\.venv\Scripts\python.exe" -m mntrapteam.state_team_lock_cli write

Then regenerate:
    & ".\.venv\Scripts\python.exe" -m mntrapteam.mens_baseline_targets_cli

Rules implemented:
- HAA is the hard gate after the MN State Shoot.
- Zone HAA takes precedence over State for the category lock because Zone occurs first.
- Qualifying category locks the State Team pool for the target year.
- SBV maps to Men's Open.
