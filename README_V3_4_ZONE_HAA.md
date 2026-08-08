# MNTrapTeam 3.4.0 — Zone HAA Live Sync

A Zone HAA qualifies only when:
1. the shooter completed the required Zone HAA components, and
2. the shoot zone matches the shooter's verified resident Minnesota zone.

Use:
    python -m mntrapteam.zone_haa_cli discover --start-id 2000 --end-id 2100
    python -m mntrapteam.zone_haa_cli sync --zone SOUTHERN --shoot-id <ID>
    python -m mntrapteam.zone_haa_cli sync --zone CENTRAL --shoot-id <ID>
    python -m mntrapteam.zone_haa_cli sync --zone NORTHERN --shoot-id <ID>
    python -m mntrapteam.zone_haa_cli pending
