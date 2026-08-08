from mntrapteam.live_display import (
    actionable_missing_requirements,
    rank_by_live_hoa,
)


def test_highest_hoa_first_even_if_red():
    rows = [
        {"display_name": "Green", "live_hoa": 92.0, "eligible": True},
        {"display_name": "Red", "live_hoa": 95.0, "eligible": False},
    ]
    result = rank_by_live_hoa(rows, 1)
    assert result["rows"][0]["display_name"] == "Red"
    assert result["rows"][0]["projected_rank"] == 1


def test_actionable_requirements():
    progress = {
        "singles": (1500, 1500),
        "handicap": (1000, 1200),
        "doubles": (1000, 1000),
        "mn_singles": (700, 700),
        "mn_handicap": (650, 700),
        "mn_doubles": (400, 400),
        "clubs": (3, 4),
        "haa": (0, 1),
    }
    text = actionable_missing_requirements(progress)
    assert "Need 200 Handicap targets" in text
    assert "Need 50 MN Handicap targets" in text
    assert "Need 1 MN club" in text
    assert "Need qualifying HAA" in text
