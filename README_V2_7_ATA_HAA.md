# MNTrapTeam 2.7.0 - Automatic ATA HAA Results Import

ATA numbers are no longer expected to be entered manually.

This importer accepts a local PDF or public PDF URL containing columns such as:

- Name
- State
- Score
- ATA No.

It upserts each shooter by ATA number and creates the HAA qualification record.

Use `PARTIAL` for trophy/winner sheets and `COMPLETE` only for a complete HAA
participant or standings report. Absence from a PARTIAL report never means a
shooter failed to complete the HAA.

## Apply

```powershell
cd H:\MNTrapTeam\MNTrapTeam
& ".\.venv\Scripts\python.exe" .\Apply_v2.7.0.py
& ".\.venv\Scripts\python.exe" -m pytest -q tests
```
