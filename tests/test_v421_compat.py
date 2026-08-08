from mntrapteam.live_dashboard import _hoa_from_disciplines, _season_values

def test_legacy_dashboard_helpers_exist():
    values = _season_values(
        {
            "singles_targets": 100,
            "singles_hits": 95,
            "handicap_targets": 100,
            "handicap_hits": 90,
            "doubles_targets": 100,
            "doubles_hits": 85,
        }
    )
    assert round(_hoa_from_disciplines(values), 2) == 90.00

def test_partial_disciplines_keep_legacy_behavior():
    values = {
        "singles": {"targets": 100, "hits": 95, "average": 95.0},
        "handicap": {"targets": 0, "hits": 0, "average": 0.0},
        "doubles": {"targets": 0, "hits": 0, "average": 0.0},
    }
    assert _hoa_from_disciplines(values) == 95.0
