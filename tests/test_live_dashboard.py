from mntrapteam.live_dashboard import (
    _hoa_from_disciplines,
    _provisional_after_baseline,
    _season_values,
    _threat_context,
)


def test_hoa_from_three_disciplines():
    values = {
        "singles": {"targets": 2000, "hits": 1899, "average": 94.95},
        "handicap": {"targets": 1600, "hits": 1422, "average": 88.875},
        "doubles": {"targets": 1700, "hits": 1555, "average": 91.470588},
    }
    assert round(_hoa_from_disciplines(values), 2) == 91.77


def test_hoa_ignores_missing_discipline():
    values = {
        "singles": {"targets": 100, "hits": 95, "average": 95.0},
        "handicap": {"targets": 100, "hits": 90, "average": 90.0},
        "doubles": {"targets": 0, "hits": 0, "average": 0.0},
    }
    assert _hoa_from_disciplines(values) == 92.5


def test_season_values_builds_averages():
    row = {
        "singles_targets": 100,
        "singles_hits": 96,
        "handicap_targets": 100,
        "handicap_hits": 89,
        "doubles_targets": 100,
        "doubles_hits": 94,
    }
    result = _season_values(row)
    assert result["singles"]["average"] == 96.0
    assert result["handicap"]["average"] == 89.0
    assert result["doubles"]["average"] == 94.0



def test_duplicate_live_sources_count_same_events_once():
    base_events = [
        ("2026-08-01", "E1 - Saturday Singles", "singles", 100, 97),
        ("2026-08-01", "E2 - Saturday Handicap", "handicap", 100, 93),
        ("2026-08-02", "E4 - Sunday Singles", "singles", 100, 98),
        ("2026-08-02", "E5 - Sunday Handicap", "handicap", 100, 94),
        ("2026-08-02", "E6 - Sunday Doubles", "doubles", 100, 93),
    ]

    rows = []
    row_id = 1

    for event_date, sos_name, discipline, targets, hits in base_events:
        event_number = sos_name.split()[0]

        rows.append({
            "id": row_id,
            "event_date": event_date,
            "event_name": sos_name,
            "discipline": discipline,
            "targets": targets,
            "hits": hits,
            "in_state": 1,
            "club_key": "MONTICELLO SPORTSMEN CLUB",
            "source": "SOS Clays",
            "official": 0,
        })
        row_id += 1

        rows.append({
            "id": row_id,
            "event_date": event_date,
            "event_name": f"{event_number} {discipline.upper()}",
            "discipline": discipline,
            "targets": targets,
            "hits": hits,
            "in_state": 0,
            "club_key": "2026 JOHN BERING MEMORIAL TRAPSHOOT.",
            "source": "ShootScoreBoard recent-scout",
            "official": 0,
        })
        row_id += 1

    class FakeDatabase:
        def query(self, sql, params=()):
            return rows

    result = _provisional_after_baseline(
        FakeDatabase(),
        shooter_id=69,
        through_date="2026-07-19",
    )

    assert len(result["rows"]) == 5
    assert result["disciplines"]["singles"] == {
        "targets": 200,
        "hits": 195,
    }
    assert result["disciplines"]["handicap"] == {
        "targets": 200,
        "hits": 187,
    }
    assert result["disciplines"]["doubles"] == {
        "targets": 100,
        "hits": 93,
    }
    assert sum(
        item["targets"] for item in result["disciplines"].values()
    ) == 500
    assert result["mn"] == {
        "singles": 200,
        "handicap": 200,
        "doubles": 100,
    }



def test_threat_context_for_tenth_place_shooter():
    me = {
        "current_hoa": 92.042,
        "current_eligible": True,
        "qualified_rank": 10,
    }
    threats = [
        {
            "current_hoa": 93.0 + i / 100,
            "current_eligible": False,
        }
        for i in range(13)
    ]

    result = _threat_context([me] + threats, me, team_size=16)

    assert result["higher_hoa_unqualified"] == 13
    assert result["threats_needed_to_displace"] == 7
    assert result["threat_risk"] is True
