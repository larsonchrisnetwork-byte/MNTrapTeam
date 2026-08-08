# MNTrapTeam 3.9.1 — Zone Residency Data Audit

Read-only audit for the three Northern Zone event-complete candidates.

It inspects:
- the full shooter record;
- other linked database tables containing city/county/state/address-type fields.

It does not assign a zone and does not change the database.

Run:

    & ".\.venv\Scripts\python.exe" -m mntrapteam.zone_residency_audit_cli

Zone HAA policy:
- completing the Zone HAA events is necessary but not sufficient;
- the shooter must reside in that same MTA zone;
- club/shoot location is never used as a substitute for shooter residence.
