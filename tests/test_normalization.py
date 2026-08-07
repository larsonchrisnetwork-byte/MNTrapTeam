import pytest

from mntrapteam.normalization import (
    inferred_state,
    normalize_event_date,
    normalize_shoot_name,
)


def test_date_normalization():
    assert normalize_event_date("7/19/2026") == "2026-07-19"
    assert normalize_event_date("2026-07-19") == "2026-07-19"


def test_shoot_alias_normalization():
    assert normalize_shoot_name("MINNESOTA TRAP ASSN") == "MINNESOTA STATE SHOOT"
    assert normalize_shoot_name("2026 MN STATE SHOOT") == "MINNESOTA STATE SHOOT"


def test_state_inference():
    assert inferred_state("MINNESOTA TRAP ASSN") == "MN"
    assert inferred_state("UTAH TRAPSHOOTING ASSOC") == "UT"
