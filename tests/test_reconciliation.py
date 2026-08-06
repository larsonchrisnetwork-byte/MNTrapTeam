from mntrapteam.reconciliation import (
    STATUS_DISPUTED,
    STATUS_PROVISIONAL,
    STATUS_RECONCILED,
    match_key,
    reconcile_group,
    totals_from_events,
)


def row(*, row_id, source, targets=100, hits=95, official=0,
        imported_at="2026-08-01T12:00:00"):
    return {
        "id": row_id,
        "shooter_id": 1,
        "season": 2026,
        "event_date": "2026-07-19",
        "shoot_name": "Buffalo Gun Club",
        "shoot_number": "4359",
        "event_name": "",
        "discipline": "doubles",
        "targets": targets,
        "hits": hits,
        "source": source,
        "official": official,
        "imported_at": imported_at,
    }


def test_provisional_event_is_used_immediately():
    result = reconcile_group([row(row_id=1, source="shootscoreboard")])
    assert result["status"] == STATUS_PROVISIONAL
    assert result["selected"]["source"] == "shootscoreboard"


def test_matching_myata_reconciles_provisional():
    result = reconcile_group([
        row(row_id=1, source="shootscoreboard"),
        row(row_id=2, source="myata", official=1),
    ])
    assert result["status"] == STATUS_RECONCILED
    assert result["selected"]["source"] == "myata"


def test_myata_disagreement_is_disputed_and_official_wins():
    result = reconcile_group([
        row(row_id=1, source="sosclays", hits=97),
        row(row_id=2, source="myata", hits=96, official=1),
    ])
    assert result["status"] == STATUS_DISPUTED
    assert result["selected"]["hits"] == 96


def test_higher_priority_fast_source_wins_before_official():
    result = reconcile_group([
        row(row_id=1, source="shootscoreboard", hits=95),
        row(row_id=2, source="ata_scores", hits=96,
            imported_at="2026-08-02T12:00:00"),
    ])
    assert result["status"] == STATUS_PROVISIONAL
    assert result["selected"]["source"] == "ata_scores"


def test_match_key_prefers_shoot_number():
    assert "NUMBER:4359" in match_key(row(row_id=1, source="shootscoreboard"))


def test_totals_use_selected_events():
    events = [
        {
            "discipline": "singles",
            "targets": 100,
            "hits": 98,
            "reconciliation_status": STATUS_RECONCILED,
        },
        {
            "discipline": "doubles",
            "targets": 100,
            "hits": 95,
            "reconciliation_status": STATUS_PROVISIONAL,
        },
    ]
    totals = totals_from_events(events)
    assert totals["disciplines"]["singles"]["average"] == 98.0
    assert totals["total_targets"] == 200
