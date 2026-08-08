# MNTrapTeam 3.9.4 — Pre-selection Residence Capture

Fixes the Sparta, IL false residence problem.

MyATA shows the shooter's residence city in the Search/Buddies result row,
before the shooter is opened. Once the shooter is selected and scores are
displayed, that residence text disappears and other site-location text can
appear instead.

v3.9.4 therefore:

1. opens Search/Buddies;
2. searches the exact ATA number;
3. captures the visible result row text;
4. parses CITY, ST from that row;
5. does NOT open the shooter.

Read-only. No database or Zone assignments are changed.
