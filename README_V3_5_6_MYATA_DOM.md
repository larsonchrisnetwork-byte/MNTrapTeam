# MNTrapTeam 3.5.6 — MyATA Rendered Target Inspector

The other-shooter 2026 target history is visible in MyATA but did not produce
a distinct XHR/fetch response during capture.

This build reads the rendered browser DOM instead.

Run:

    & ".\.venv\Scripts\python.exe" -m mntrapteam.myata_dom_cli

Search ATA 2523333, open Aiden Weber, open his 2026 targets, and leave that
target table visible. The inspector prints the visible target/statistics tables
and saves local DOM structure for selector development.

If the table contains the season totals and averages we need, the next importer
can automate Search/Buddies one HAA-qualified shooter at a time using the same
authenticated browser profile.
