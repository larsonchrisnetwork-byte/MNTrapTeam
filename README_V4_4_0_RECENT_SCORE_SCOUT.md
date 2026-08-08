# MNTrapTeam 4.4.0 — Recent Score Scout

MVP for the final weeks of the target year.

Preview all recent ShootScoreBoard scores for the frozen Men's HAA pool that
are newer than each shooter's MyATA official-through date:

    & ".\.venv\Scripts\python.exe" -m mntrapteam.recent_score_scout_cli preview

If needed, widen discovery:

    --id-scan 1900:2300

After reviewing the preview:

    & ".\.venv\Scripts\python.exe" -m mntrapteam.recent_score_scout_cli write

The scout:
- tracks only the locked Men's HAA pool;
- compares each shooter to their own MyATA cutoff;
- ignores already-present identical score rows;
- holds multi-day shoots overlapping a cutoff for review;
- does NOT rebuild official MyATA season_stats.

For safety, this first version does not infer Minnesota shoot location from the
shooter STATE column. Newly found scores immediately improve Current HOA and
total targets; Minnesota in-state credit will be classified separately.
