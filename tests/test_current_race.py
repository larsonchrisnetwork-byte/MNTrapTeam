from pathlib import Path
from types import SimpleNamespace

import pytest

from mntrapteam.current_race import (
    TARGET_YEAR,
    discover_minnesota_shoots_from_html,
    in_target_year,
    read_candidate_csv,
    sync_current_race,
    validate_loaded_shoot,
    write_candidate_csv,
)


def fixture_html():
    return Path("tests/fixtures/ssb_2026_listing.html").read_text(encoding="utf-8")


def test_target_year_boundaries():
    assert TARGET_YEAR == 2026
    assert in_target_year("2025-09-01", "2026-08-31")
    assert not in_target_year("2025-06-14", "2025-06-15")
    assert not in_target_year("2026-09-01", "2026-09-02")


def test_discovery_filters_minnesota_and_marks_target_year():
    candidates = discover_minnesota_shoots_from_html(fixture_html())
    assert [candidate.shoot_id for candidate in candidates] == [1957, 2101, 2202]
    current = [candidate.shoot_id for candidate in candidates if candidate.in_target_year]
    assert current == [2101, 2202]


def test_queue_round_trip(tmp_path):
    candidates = discover_minnesota_shoots_from_html(fixture_html())
    path = write_candidate_csv(candidates, tmp_path / "queue.csv")
    loaded = read_candidate_csv(path)
    assert len(loaded) == 3
    assert loaded[0].shoot_id == 1957
    assert loaded[0].selected is False
    assert loaded[1].selected is True


def test_validate_rejects_2025_calendar_shoot_outside_target_year():
    shoot = SimpleNamespace(
        name="2025 Northern Zone",
        start_date="2025-06-14",
        end_date="2025-06-15",
    )
    with pytest.raises(ValueError, match="outside the active 2026 target year"):
        validate_loaded_shoot(shoot)


class Database:
    pass


def test_sync_skips_deselected_out_of_season_shoot():
    candidates = discover_minnesota_shoots_from_html(fixture_html())
    historical = next(item for item in candidates if item.shoot_id == 1957)

    def loader(shoot_id):
        raise AssertionError("loader should not run")

    summary = sync_current_race(Database(), [historical], loader=loader)
    assert summary.attempted == 0
    assert summary.failed_shoots == 0
