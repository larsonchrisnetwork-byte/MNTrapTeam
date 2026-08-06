import pytest

from mntrapteam.event_intelligence import (
    club_performance,
    event_intelligence,
    monthly_performance,
    personal_bests,
    recent_form,
    season_event_summary,
)


EVENTS = [
    {
        "event_date": "2026-05-01",
        "event_name": "May Shoot",
        "discipline": "singles",
        "targets": 100,
        "hits": 98,
        "average": 98.0,
        "club_display": "Club A",
        "month": "2026-05",
        "in_state": 1,
        "straight": False,
    },
    {
        "event_date": "2026-06-01",
        "event_name": "June Shoot",
        "discipline": "singles",
        "targets": 100,
        "hits": 100,
        "average": 100.0,
        "club_display": "Club B",
        "month": "2026-06",
        "in_state": 1,
        "straight": True,
    },
    {
        "event_date": "2026-06-01",
        "event_name": "June Shoot",
        "discipline": "handicap",
        "targets": 100,
        "hits": 92,
        "average": 92.0,
        "club_display": "Club B",
        "month": "2026-06",
        "in_state": 1,
        "straight": False,
    },
    {
        "event_date": "2026-07-01",
        "event_name": "July Shoot",
        "discipline": "doubles",
        "targets": 100,
        "hits": 95,
        "average": 95.0,
        "club_display": "Club C",
        "month": "2026-07",
        "in_state": 0,
        "straight": False,
    },
]


def test_summary_counts_targets_clubs_and_straights():
    summary = season_event_summary(EVENTS)
    assert summary["total_targets"] == 400
    assert summary["total_hits"] == 385
    assert summary["clubs"] == 3
    assert summary["mn_clubs"] == 2
    assert summary["total_straights"] == 1
    assert summary["disciplines"][0]["average"] == pytest.approx(99.0)


def test_recent_form_uses_newest_scores():
    result = recent_form(EVENTS, 100)
    singles = next(row for row in result if row["discipline"] == "singles")
    assert singles["targets"] == 100
    assert singles["average"] == pytest.approx(100.0)


def test_personal_bests_select_highest_average():
    bests = personal_bests(EVENTS)
    singles = next(row for row in bests if row["discipline"] == "singles")
    assert singles["hits"] == 100
    assert singles["event_name"] == "June Shoot"


def test_club_and_month_aggregation():
    clubs = club_performance(EVENTS)
    club_b_singles = next(
        row
        for row in clubs
        if row["club_display"] == "Club B"
        and row["discipline"] == "singles"
    )
    assert club_b_singles["average"] == pytest.approx(100.0)
    months = monthly_performance(EVENTS)
    assert len([row for row in months if row["month"] == "2026-06"]) == 2


def test_recent_form_rejects_invalid_window():
    with pytest.raises(ValueError):
        recent_form(EVENTS, 0)


class Database:
    def query(self, sql, params=()):
        if "from scores sc" not in " ".join(sql.lower().split()):
            return []
        rows = []
        for index, event in enumerate(EVENTS, 1):
            rows.append(
                {
                    "id": index,
                    "event_date": event["event_date"],
                    "event_name": event["event_name"],
                    "discipline": event["discipline"],
                    "targets": event["targets"],
                    "hits": event["hits"],
                    "in_state": event["in_state"],
                    "club_key": event["club_display"],
                    "source": "test",
                    "official": 0,
                    "shoot_name": event["event_name"],
                    "club": event["club_display"],
                    "city": "",
                    "state": "MN" if event["in_state"] else "ND",
                }
            )
        return rows


def test_full_event_intelligence_payload():
    result = event_intelligence(Database(), 1, 2026, 100)
    assert result["summary"]["event_rows"] == 4
    assert len(result["personal_bests"]) == 3
    assert result["events"][0]["event_date"] == "2026-07-01"
