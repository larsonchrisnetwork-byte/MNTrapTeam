# MNTrapTeam 3.9.9

Adds provenance-preserving Zone HAA tables and records the three Northern Zone
candidates whose evidence is fully verified:

- Craig Isaacson — ATA 1776550 — St Michael, MN
- Russ Hiltz — ATA 0416492 — Bemidji, MN
- Troy Haverly — ATA 2805615 — New London, MN

Before writing, the importer independently verifies that the database contains:

- 200 N Zone Championship Singles targets
- 100 N Zone Championship Handicap targets
- 100 N Zone Championship Doubles targets

Residence evidence comes from MyATA Search/Buddies before shooter selection.

Zone HAA is kept separate from State HAA so source/provenance is preserved.

Run:
    python -m mntrapteam.zone_haa_record_north_cli
    python -m mntrapteam.zone_haa_report_cli
