# MNTrapTeam 4.3.2 — Logged-in MyATA baseline fallback

Purpose: get the live Men's race usable quickly.

When the target ATA number is the logged-in shooter:
1. Try the normal My Scores path.
2. If that path cannot find/open the season, automatically use Search/Buddies.
3. Scrape and save the official baseline exactly like any other shooter.

This specifically addresses the 2026 Christopher Larson baseline failure seen
during the 68-man Men's HAA candidate refresh.
