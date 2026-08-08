from mntrapteam.live_dashboard import _hoa_from_disciplines, _season_values


def test_hoa_from_three_disciplines():
    values = {
        "singles": {"targets": 2000, "hits": 1899, "average": 94.95},
        "handicap": {"targets": 1600, "hits": 1422, "average": 88.875},
        "doubles": {"targets": 1700, "hits": 1555, "average": 91.470588},
    }
    assert round(_hoa_from_disciplines(values), 2) == 91.77


def test_hoa_ignores_missing_discipline():
    values = {
        "singles": {"targets": 100, "hits": 95, "average": 95.0},
        "handicap": {"targets": 100, "hits": 90, "average": 90.0},
        "doubles": {"targets": 0, "hits": 0, "average": 0.0},
    }
    assert _hoa_from_disciplines(values) == 92.5


def test_season_values_builds_averages():
    row = {
        "singles_targets": 100,
        "singles_hits": 96,
        "handicap_targets": 100,
        "handicap_hits": 89,
        "doubles_targets": 100,
        "doubles_hits": 94,
    }
    result = _season_values(row)
    assert result["singles"]["average"] == 96.0
    assert result["handicap"]["average"] == 89.0
    assert result["doubles"]["average"] == 94.0
