# MNTrapTeam 3.2.0 — First Usable Live Team Dashboard

The new **2026 Live Team** tab centers the application on the current team race.

It shows:

- mandatory HAA gate and route,
- complete eligibility,
- live and official HOA,
- pending and disputed targets,
- live cut line and gap,
- live discipline target counts,
- Minnesota club count,
- missing requirements,
- active data source.

HAA-qualified shooters appear first. Shooters outside the HAA gate cannot set
the live cut line.

Apply:

    & ".\.venv\Scripts\python.exe" .\Apply_v3.2.0.py
    & ".\.venv\Scripts\python.exe" -m pytest -q tests
    .\Run_MNTrapTeam.bat
