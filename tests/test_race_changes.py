import json
import pytest

from mntrapteam.race_changes import (
    compare_rankings,
    latest_team_snapshot,
    race_changes_from_latest_snapshot,
)


def row(ata, name, rank, hoa, selected):
    return {
        "ata_number": ata,
        "display_name": name,
        "rank": rank,
        "hoa": hoa,
        "selected": selected,
    }


def test_compare_rankings_tracks_moves_and_team_changes():
    previous = [
        row("1", "One", 1, 95.0, True),
        row("2", "Two", 2, 94.0, True),
        row("3", "Three", 3, 93.0, False),
    ]
    current = [
        row("1", "One", 2, 95.1, True),
        row("2", "Two", 3, 94.0, False),
        row("3", "Three", 1, 96.0, True),
    ]
    result = compare_rankings(previous, current)

    three = next(change for change in result["changes"] if change["key"] == "3")
    two = next(change for change in result["changes"] if change["key"] == "2")

    assert three["rank_change"] == 2
    assert three["team_change"] == "Entered team"
    assert two["team_change"] == "Left team"
    assert result["cut_line_change"] == pytest.approx(2.0)


def test_compare_rankings_handles_new_and_removed():
    result = compare_rankings(
        [row("1", "One", 1, 95.0, True)],
        [row("2", "Two", 1, 96.0, True)],
    )
    assert {change["change_type"] for change in result["changes"]} == {
        "New shooter",
        "Removed shooter",
    }


class Database:
    def __init__(self, payload):
        self.payload = payload

    def query(self, sql, params=()):
        return [{
            "id": 5,
            "season": 2026,
            "label": "Before weekend",
            "created_at": "2026-07-01T10:00:00",
            "payload": json.dumps(self.payload),
        }]


class TeamService:
    def rankings(self, season, team):
        return [row("1", "One", 1, 96.0, True)]


def test_latest_team_snapshot_extracts_team_rows():
    db = Database({"MEN": [row("1", "One", 1, 95.0, True)]})
    snapshot = latest_team_snapshot(db, 2026, "MEN")
    assert snapshot["label"] == "Before weekend"
    assert snapshot["rows"][0]["hoa"] == 95.0


def test_compare_from_latest_snapshot():
    db = Database({"MEN": [row("1", "One", 1, 95.0, True)]})
    result = race_changes_from_latest_snapshot(db, TeamService(), 2026, "MEN")
    assert result["has_snapshot"] is True
    assert result["changes"][0]["hoa_change"] == pytest.approx(1.0)


def test_no_snapshot_returns_message():
    class EmptyDatabase:
        def query(self, sql, params=()):
            return []

    result = race_changes_from_latest_snapshot(
        EmptyDatabase(),
        TeamService(),
        2026,
        "MEN",
    )
    assert result["has_snapshot"] is False
    assert "No saved snapshot" in result["message"]
