from mntrapteam.season import season_bounds, season_for_date

def test_season_bounds():
    assert season_bounds(2026) == ('2025-09-01','2026-08-31')

def test_season_for_date():
    assert season_for_date('2025-09-01') == 2026
    assert season_for_date('2026-08-31') == 2026
    assert season_for_date('2026-09-01') == 2027
