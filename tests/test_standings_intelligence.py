from dataclasses import dataclass

import pytest

from mntrapteam.calculations import (
    average_needed_for_target,
    project_season,
    team_rankings,
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
        return Result(bool(row.get("eligible_flag", True)), [])


def shooter(name, hoa_value, eligible=True):
    # Equal averages in all disciplines produce the requested HOA.
    hits = round(hoa_value * 10)
    return {
        "display_name": name,
        "category": "MEN",
        "eligible_flag": eligible,
        "singles_hits": hits,
        "singles_targets": 1000,
        "handicap_hits": hits,
        "handicap_targets": 1000,
        "doubles_hits": hits,
        "doubles_targets": 1000,
    }


def test_rankings_include_cut_line_and_gap():
    rows = [
        shooter("One", 96),
        shooter("Two", 95),
        shooter("Three", 94),
        shooter("Ineligible", 99, eligible=False),
    ]
    ranked = team_rankings(rows, Rules(), "MEN")

    assert ranked[0]["display_name"] == "One"
    assert ranked[1]["selected"] is True
    assert ranked[1]["cut_line_hoa"] == pytest.approx(95)
    third = next(row for row in ranked if row["display_name"] == "Three")
    assert third["hoa_gap_to_cut"] == pytest.approx(-1)
    assert third["birds_per_300_gap"] == pytest.approx(-3)


def test_cut_line_is_none_until_team_is_full():
    rules = Rules()
    rules.rules = {"teams": {"MEN": {"size": 4}}}
    ranked = team_rankings([shooter("One", 96), shooter("Two", 95)], rules, "MEN")
    assert all(row["cut_line_hoa"] is None for row in ranked)


def test_average_needed_for_fixed_future_targets():
    # 95% on 1,000 targets, aiming for 96% after 1,000 more:
    assert average_needed_for_target(950, 1000, 1000, 96) == pytest.approx(97)
    assert average_needed_for_target(0, 1000, 100, 99) is None


def test_project_multiple_disciplines():
    row = {
        "singles_hits": 950,
        "singles_targets": 1000,
        "handicap_hits": 900,
        "handicap_targets": 1000,
        "doubles_hits": 920,
        "doubles_targets": 1000,
    }
    projected = project_season(
        row,
        {
            "singles": (100, 98),
            "doubles": (100, 96),
        },
    )
    assert projected["singles_targets"] == 1100
    assert projected["doubles_targets"] == 1100
    assert projected["handicap_targets"] == 1000
    assert 92 < projected["hoa"] < 94
