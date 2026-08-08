# MNTrapTeam 3.9.3 — Residence Capture v2

The v3.9.2 capture assumed MyATA left the Search/Buddies result button visible
after opening the shooter. Production testing showed that it often disappears.

v3.9.3 searches:
1. visible result/selected buttons;
2. rendered body text;
3. compact DOM text elements;

for CITY, ST patterns after the exact-ATA shooter has opened.

If several locations are present, the tool reports ambiguity instead of
guessing.

Read-only. No Zone assignment or database write is performed.
