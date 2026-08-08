# MNTrapTeam 3.8.0 — Shooter Identity Guard

Adds a permanent identity rule:

    ATA number = authoritative shooter identity
    Name       = display/search aid only

This prevents same-name shooters such as Sr./Jr. family members from being
merged or treated as the same person solely by name.

New audit command:

    & ".\.venv\Scripts\python.exe" -m mntrapteam.identity_audit_cli

The audit reports:
- duplicate ATA numbers (critical);
- same-name/different-ATA groups (valid, but must remain separate).

This identity layer will be used by the upcoming Zone HAA importer.
