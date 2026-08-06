from dataclasses import dataclass

import pytest

from mntrapteam.analytics import (
    discipline_progress,
    event_history,
    personal_progress,
    rolling_event_average,
)


class FakeDatabase:
    def __init__(self):
        self.shooter = {
            "id": 1,
            "ata_number": "1234567",
            "display_name": "Test Shooter",
            "category": "MEN",
            "active": 1,
        }

    def query(self, sql, params=()):
        normalized = " ".join(sql.split()).lower()
        if "from shooters where ata_number" in normalized:
            return [self.shooter] if params[0] == "1234567" else []
        if "from scores sc" in normalized:
            return [
                {
                    "id": 2,
                    "event_date": "2026-07-01",
                    "event_name": "July Shoot",
                    "discipline": "singles",
                    "targets": 100,
                    "hits": 98,
                    "in_state": 1,
                    "club_key": "Club A",
                    "source": "ShootScoreBoard",
                    "official": 0,
                    "shoot_name": "July Shoot",
                    "club": "Club A",
                    "city": "Town",
                    "state": "MN",
                },
                {
                    "id": 1,
                    "event_date": "2026-06-01",
                    "event_name": "June Shoot",
                    "discipline": "singles",
                    "targets": 100,
                    "hits": 96,
                    "in_state": 1,
                    "club_key": "Club B",
                    "source": "ShootScoreBoard",
                    "official": 0,
                    "shoot_name": "June Shoot",
                    "club": "Club B",
                    "city": "",
                    "state": "MN",
                },
            ]
        if "group by discipline" in normalized:
            return [
                {
                    "discipline": "singles",
                    "targets": 200,
                    "hits": 194,
                    "mn_targets": 200,
                    "events": 2,
                    "mn_clubs": 2,
                }
            ]
        return []


@dataclass
class Eligibility:
    eligible: bool
    reasons: list[str]


class Rules:
    def team_for_category(self, category):
        return "MEN"


class TeamService:
    rules = Rules()

    def season_rows(self, season):
        return [
            {
                "id": 1,
                "display_name": "Test Shooter",
                "category": "MEN",
                "hoa": 92.5,
                "eligibility": Eligibility(False, ["Need more doubles targets"]),
            }
        ]

    def rankings(self, season, team):
        return [
            {
                "id": 1,
                "rank": 17,
                "eligible_rank": None,
                "selected": False,
                "hoa": 92.5,
                "cut_line_hoa": 92.7,
                "hoa_gap_to_cut": -0.2,
            }
        ]


def test_event_history_adds_average_and_location():
    events = event_history(FakeDatabase(), 1, 2026)
    assert events[0]["average"] == pytest.approx(98)
    assert events[0]["location"] == "Club A, Town, MN"
    assert events[0]["mn"] is True


def test_discipline_progress_fills_missing_disciplines():
    progress = discipline_progress(FakeDatabase(), 1, 2026)
    assert progress["singles"]["average"] == pytest.approx(97)
    assert progress["singles"]["mn_clubs"] == 2
    assert progress["handicap"]["targets"] == 0
    assert progress["doubles"]["targets"] == 0


def test_rolling_average_uses_most_recent_events():
    events = event_history(FakeDatabase(), 1, 2026)
    assert rolling_event_average(events, "singles", 150) == pytest.approx(97)
    with pytest.raises(ValueError):
        rolling_event_average(events, "singles", 0)


def test_personal_progress_combines_rank_and_eligibility():
    result = personal_progress(FakeDatabase(), TeamService(), 2026, "123-4567")
    assert result["found"] is True
    assert result["has_stats"] is True
    assert result["team"] == "MEN"
    assert result["ranking"]["rank"] == 17
    assert result["eligible"] is False
    assert "doubles" in result["eligibility_reasons"][0].lower()


def test_personal_progress_handles_unknown_ata():
    result = personal_progress(FakeDatabase(), TeamService(), 2026, "9999999")
    assert result["found"] is False
