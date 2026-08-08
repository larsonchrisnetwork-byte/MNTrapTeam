# MNTrapTeam 4.3.0 — Men's Race Integration

Built directly from the current uploaded project.

- Fixes `mens_race_cli.py` to use the real `RulesEngine` and `TeamService`.
- Adds a `Baseline Ready` column to the 2026 Live Team table.
- Adds `mens_baseline_targets_cli` to generate a targeted MyATA refresh file
  for HAA-qualified Men's contenders with no official-through date.
- Keeps provisional score overlays disabled when the baseline cutoff is unknown.
- Keeps qualified and not-yet-qualified Men's shooters together in Current-HOA order.
