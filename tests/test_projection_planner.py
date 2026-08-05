from dataclasses import dataclass

from mntrapteam.planner import (
    project_plan,
    projected_team_rank,
    required_uniform_average_for_cut,
)


@dataclass
class Result:
    eligible: bool
    reasons: list[str]


class Rules:
    rules = {"teams": {"MEN": {"size": 2}}}

    def team_for_category(self, category):
        return "MEN"

    def check(self, row, requested_team=None):
        return Result(True, [])


def row(shooter_id, name, value):
    hits = round(value * 10)
    return {
        "id": shooter_id,
        "display_name": name,
        "category": "MEN",
        "singles_hits": hits,
        "singles_targets": 1000,
        "handicap_hits": hits,
        "handicap_targets": 1000,
        "doubles_hits": hits,
        "doubles_targets": 1000,
    }


def test_three_discipline_plan():
    projected = project_plan(
        row(1, "Chris", 90),
        {"singles": (100, 100), "handicap": (200, 95), "doubles": (0, 0)},
    )
    assert projected["singles_targets"] == 1100
    assert projected["handicap_targets"] == 1200
    assert projected["hoa"] > 90


def test_projected_rank_moves_shooter():
    rows = [row(1, "Chris", 90), row(2, "Second", 95), row(3, "Third", 94)]
    result = projected_team_rank(
        rows,
        1,
        {"singles": (5000, 100), "handicap": (5000, 100), "doubles": (5000, 100)},
        Rules(),
        "MEN",
    )
    assert result["selected"] is True
    assert result["rank"] <= 2


def test_required_average_for_cut():
    rows = [row(1, "Chris", 90), row(2, "Second", 95), row(3, "Third", 94)]
    needed = required_uniform_average_for_cut(
        rows,
        1,
        {"singles": 5000, "handicap": 5000, "doubles": 5000},
        Rules(),
        "MEN",
    )
    assert needed is not None
    assert 94 < needed <= 100


def test_impossible_plan_returns_none():
    rows = [row(1, "Chris", 10), row(2, "Second", 99), row(3, "Third", 98)]
    needed = required_uniform_average_for_cut(
        rows,
        1,
        {"singles": 100, "handicap": 100, "doubles": 100},
        Rules(),
        "MEN",
    )
    assert needed is None
