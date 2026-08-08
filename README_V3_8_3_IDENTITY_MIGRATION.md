# MNTrapTeam 3.8.3 — Safe Blank-ATA Migration

Migrates the seven audited legacy blank-ATA shooter rows into their
ATA-numbered counterparts.

Policy:
- ATA-numbered shooter survives.
- Unique scores are copied to the target shooter.
- Duplicate scores are skipped.
- season_stats moves only when the target lacks that season.
- Same-season ATA-numbered season_stats is preserved.
- Orphan-linked rows are deleted only after migration.
- Orphan shooter is deleted only if no known shooter references remain.

Run after applying:

    & ".\.venv\Scripts\python.exe" -m mntrapteam.identity_migrate_cli

Then verify with:

    & ".\.venv\Scripts\python.exe" -m mntrapteam.identity_audit_cli
