# MNTrapTeam 3.5.1 — SOS High-Gun Request Capture

This release captures the POST body sent to:

    /1/shoots/{shootId}/shootHighGunReport

The purpose is to determine exactly which events/filter SOS is using for the
HAA report.

For the 2026 MN State Shoot, eventsData already shows:

- E12 / eventId 17360 = 100 Doubles, haaEvent=1
- E13 / eventId 17361 = 200 Singles, haaEvent=1
- E15 / eventId 19241 = 100 Handicap, haaEvent=1

If the request body confirms those events or an HAA report filter, then a row
with eventsCompleted=3 can be treated as completing the State HAA route.

Run:

    & ".\.venv\Scripts\python.exe" -m mntrapteam.sos_request_cli
