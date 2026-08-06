# MNTrapTeam 2.0.0 consolidation

This release integrates the already-present `analytics.py` and `race.py`
engines into the permanent GUI.

## Apply

```powershell
cd H:\MNTrapTeam\MNTrapTeam
& ".\.venv\Scripts\python.exe" .\Apply_v2.0.0.py
& ".\.venv\Scripts\python.exe" -m pytest -q tests
.\Run_MNTrapTeam.bat
```

After both tabs open and the tests pass:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\Cleanup_Obsolete_Upgrade_Files.ps1 -WhatIf
.\Cleanup_Obsolete_Upgrade_Files.ps1
& ".\.venv\Scripts\python.exe" -m pytest -q tests
git add -A
git commit -m "Consolidate My Progress and Team Race into version 2.0"
git push
```
