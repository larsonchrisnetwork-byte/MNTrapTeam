# MNTrapTeam 3.9.7

v3.9.5 proved that directly filling the visible `ATA Number` field while
Search/Buddies is already open produces the residence result button.

v3.9.6 changed that sequence and failed.

v3.9.7 intentionally restores the proven behavior:
- user leaves Search/Buddies visible;
- locate input[placeholder="ATA Number"];
- fill ATA number;
- wait;
- read visible result button;
- parse CITY, ST;
- replace ATA number for next candidate;
- never click a shooter and never navigate away between candidates.

Read-only.
