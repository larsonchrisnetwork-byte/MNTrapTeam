import pytest

from mntrapteam.race import (
    classify_race_status,
    race_summary,
    shooter_race_position,
    team_race,
)


def row(shooter_id, name, hoa, eligible=True, selected=False, rank=1):
    return {
        "id": shooter_id,
        "display_name": name,
        "hoa": hoa,
        "eligible": eligible,
        "selected": selected,
        "rank": rank,
        "eligibility_reasons": "" if eligible else "Need more doubles targets",
    }


def sample_rankings():
    return [
        row(1, "First", 96.0, True, True, 1),
        row(2, "Second", 95.0, True, True, 2),
        row(3, "Bubble", 94.6, True, False, 3),
        row(4, "Close Ineligible", 94.5, False, False, 4),
        row(5, "Far", 90.0, True, False, 5),
    ]


def test_summary_uses_last_selected_as_cut():
    summary = race_summary(sample_rankings(), 2)
    assert summary["cut_line_hoa"] == pytest.approx(95.0)
    assert summary["selected"] == 2
    assert summary["open_positions"] == 0


def test_race_includes_team_and_bubble():
    race = team_race(sample_rankings(), 2, bubble_width=0.75, include_outside=0)
    names = [item["display_name"] for item in race["rows"]]
    assert names == ["First", "Second", "Bubble", "Close Ineligible"]
    close = next(item for item in race["rows"] if item["id"] == 4)
    assert close["race_status"] == "Bubble — Ineligible"
    assert close["birds_per_300_gap"] == pytest.approx(-1.5)


def test_open_team_has_no_cut_line():
    rankings = [
        row(1, "Only", 94.0, True, True, 1),
        row(2, "Eligible", 93.0, True, False, 2),
    ]
    race = team_race(rankings, 4)
    assert race["summary"]["cut_line_hoa"] is None
    assert race["summary"]["open_positions"] == 3
    assert race["rows"][1]["race_status"] == "Eligible — Open Spot"


def test_shooter_position_returns_requested_shooter():
    found = shooter_race_position(sample_rankings(), 3, 2)
    assert found["display_name"] == "Bubble"
    assert found["hoa_gap_to_cut"] == pytest.approx(-0.4)


def test_invalid_race_arguments():
    with pytest.raises(ValueError):
        team_race([], 0)
    with pytest.raises(ValueError):
        team_race([], 1, bubble_width=-0.1)
