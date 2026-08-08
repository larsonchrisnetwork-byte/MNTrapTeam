# MNTrapTeam 3.8.1

Adds a conservative audit for legacy same-name shooter records that have a
blank ATA number.

It does NOT delete or merge anything.

Run:

    & ".\.venv\Scripts\python.exe" -m mntrapteam.identity_reference_audit_cli

The command scans tables for shooter-linked references and reports whether each
blank-ATA row is unused or still owns data. Only unreferenced rows should be
deleted automatically.
