# MNTrapTeam 3.6.7 — ATA Search/Buddies Fix

Manual inspection proved that a successful Search/Buddies ATA lookup renders a
button such as:

    WEBER, AIDEN KENITH. - MONTICELLO, MN

The previous automation was filling a generic Advanced Search input.

v3.6.7 now:

- opens Search/Buddies;
- tries each usable input inside `ata-shooter-information-center`;
- enters the ATA number;
- waits for a result button containing both the shooter's first and last name;
- clicks only that matching result;
- never accepts the generic advanced-search field merely because it accepted
  text;
- retains manual assist if MyATA's custom UI changes;
- also includes the year-cell/Score Details fallback that had not yet been
  applied.

Test with two shooters first:

    & ".\.venv\Scripts\python.exe" -m mntrapteam.myata_bulk_dom_cli `
      --season 2026 `
      --limit 2 `
      --dry-run `
      --manual-assist
