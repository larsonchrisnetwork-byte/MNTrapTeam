import pytest

from mntrapteam.myata import (
    parse_totals_from_tables,
    normalize_table,
)


def test_wide_official_totals_table():
    tables = [[
        [
            "Target Year",
            "Singles Targets",
            "Singles Average",
            "Handicap Targets",
            "Handicap Average",
            "Doubles Targets",
            "Doubles Average",
        ],
        ["2026", "2,000", "94.95", "1,600", "88.88", "1,700", "91.47"],
    ]]
    totals = parse_totals_from_tables(tables, 2026, "1234567", "Chris Larson")
    assert totals is not None
    assert totals.singles_targets == 2000
    assert totals.singles_hits == 1899
    assert totals.handicap_targets == 1600
    assert totals.doubles_targets == 1700


def test_separate_discipline_rows():
    tables = [[
        ["Target Year", "Discipline", "Targets", "Average"],
        ["2026", "Singles", "2000", "94.95"],
        ["2026", "Handicap", "1600", "88.88"],
        ["2026", "Doubles", "1700", "91.47"],
    ]]
    totals = parse_totals_from_tables(tables, 2026, "1234567")
    assert totals is not None
    assert totals.singles_targets == 2000
    assert totals.doubles_hits == round(1700 * .9147)


def test_wrong_target_year_is_ignored():
    tables = [[
        ["Target Year", "Singles Targets", "Singles Average", "Handicap Targets", "Handicap Average"],
        ["2025", "1000", "95.0", "1000", "90.0"],
    ]]
    assert parse_totals_from_tables(tables, 2026, "1234567") is None


def test_normalize_table_selects_useful_header():
    rows = [
        ["Shooter Information"],
        ["Target Year", "Discipline", "Targets", "Average"],
        ["2026", "Singles", "2000", "94.95"],
    ]
    normalized = normalize_table(rows)
    assert normalized[0]["target_year"] == "2026"
    assert normalized[0]["discipline"] == "Singles"
