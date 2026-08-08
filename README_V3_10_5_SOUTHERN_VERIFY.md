# MNTrapTeam 3.10.5

Classifies the 28 captured Southern HAA candidates by residence city/county
against the official MTA Zone Map.

Important:
- Southern-zone residents can be written as verified Zone HAA qualifiers.
- Central/Northern residents are not written.
- New Prague is deliberately AMBIGUOUS because the city spans Scott County
  (Central Zone) and Le Sueur County (Southern Zone). It is not written without
  county-level residence evidence.

Preview:
    python -m mntrapteam.zone_haa_south_verify_cli preview

Write only verified Southern residents:
    python -m mntrapteam.zone_haa_south_verify_cli write
