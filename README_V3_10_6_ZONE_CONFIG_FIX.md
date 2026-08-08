# MNTrapTeam 3.10.6

Fixes the Southern Zone classifier based on the official MTA Zone Map.

Key fixes:
- Carver County is Southern Zone.
- GLENCO normalizes to GLENCOE.
- County-to-zone definitions are moved to config/mta_zone_counties.json.
- City-to-county overrides are moved to config/mn_city_county_overrides.json.
- Unknown and ambiguous locations are reported explicitly.
- New Prague remains ambiguous because it spans Scott and Le Sueur counties.

Preview after applying:
    & ".\.venv\Scripts\python.exe" -m mntrapteam.zone_haa_south_verify_cli preview

Do not write until the preview is reviewed.
