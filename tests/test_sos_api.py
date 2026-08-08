from mntrapteam.sos_api import (
    SOSCandidate,
    SOSClient,
    SOSLocation,
    candidate_from_row,
    import_sos_shoot,
    in_target_year,
)


def test_candidate_parses_locations_json_string():
    candidate = candidate_from_row(
        {
            "shootId": 5515,
            "name": "2026 John Berning Memorial Shoot",
            "startDate": "2026-08-01",
            "endDate": "2026-08-02",
            "locations": (
                '[{"clubId":115,"clubName":"Test MN Club",'
                '"city":"Test","stateProvince":"MN"}]'
            ),
        }
    )
    assert candidate is not None
    assert candidate.is_minnesota
    assert candidate.locations[0].club_id == 115
    assert in_target_year(candidate, 2026)


class FakeSOS(SOSClient):
    def __init__(self):
        pass

    def get_shoot(self, shoot_id):
        assert shoot_id == 5515
        return {
            "events": {
                "21485": {
                    "eventId": 21485,
                    "shootId": 5515,
                    "details": {
                        "name": "Saturday Singles",
                        "eventNumber": 1,
                        "eventTypeId": 1,
                        "targetQuantity": 100,
                    },
                    "clubEvents": {"115": {"eventDate": "2026-08-01"}},
                },
                "21486": {
                    "eventId": 21486,
                    "shootId": 5515,
                    "details": {
                        "name": "Saturday Handicap",
                        "eventNumber": 2,
                        "eventTypeId": 3,
                        "targetQuantity": 100,
                    },
                    "clubEvents": {"115": {"eventDate": "2026-08-01"}},
                },
                "21487": {
                    "eventId": 21487,
                    "shootId": 5515,
                    "details": {
                        "name": "Saturday Doubles",
                        "eventNumber": 3,
                        "eventTypeId": 2,
                        "targetQuantity": 100,
                    },
                    "clubEvents": {"115": {"eventDate": "2026-08-01"}},
                },
            }
        }

    def high_gun_report(self, shoot_id, event_id, club_id):
        assert shoot_id == 5515
        assert club_id == 115
        scores = {21485: 97, 21486: 93, 21487: None}
        score = scores[event_id]
        if score is None:
            return []
        return [
            {
                "firstName": "Christopher",
                "middleName": "W",
                "lastName": "Larson",
                "ataId": "0113918",
                "class": "A",
                "category": None,
                "handicap": "26.0",
                "totalScore": score,
                "stateProvince": "MN",
            }
        ]


def test_import_uses_target_quantity_only_when_shooter_has_result(database):
    candidate = SOSCandidate(
        5515,
        "2026 John Berning Memorial Shoot",
        "2026-08-01",
        "2026-08-02",
        (SOSLocation(115, "Test MN Club", "Test", "MN"),),
    )
    result = import_sos_shoot(database, FakeSOS(), candidate, 2026)
    assert result.events_found == 3
    assert result.score_rows_imported == 2

    shooter = database.query(
        "SELECT id FROM shooters WHERE ata_number='0113918'"
    )[0]
    scores = database.query(
        "SELECT discipline,targets,hits FROM scores WHERE shooter_id=? ORDER BY discipline",
        (shooter["id"],),
    )
    assert scores == [
        {"discipline": "handicap", "targets": 100, "hits": 93},
        {"discipline": "singles", "targets": 100, "hits": 97},
    ]
    assert sum(row["targets"] for row in scores) == 200


def test_import_aggregates_same_discipline_for_reconciliation(database):
    class TwoSingles(FakeSOS):
        def get_shoot(self, shoot_id):
            payload = super().get_shoot(shoot_id)
            payload["events"]["21488"] = {
                "eventId": 21488,
                "shootId": 5515,
                "details": {
                    "name": "Sunday Singles",
                    "eventNumber": 4,
                    "eventTypeId": 1,
                    "targetQuantity": 100,
                },
                "clubEvents": {"115": {"eventDate": "2026-08-02"}},
            }
            return payload

        def high_gun_report(self, shoot_id, event_id, club_id):
            if event_id == 21488:
                return [{
                    "firstName": "Christopher",
                    "middleName": "W",
                    "lastName": "Larson",
                    "ataId": "0113918",
                    "category": None,
                    "handicap": "26.0",
                    "totalScore": 98,
                    "stateProvince": "MN",
                }]
            return super().high_gun_report(shoot_id, event_id, club_id)

    candidate = SOSCandidate(
        5515,
        "2026 John Berning Memorial Shoot",
        "2026-08-01",
        "2026-08-02",
        (SOSLocation(115, "Test MN Club", "Test", "MN"),),
    )
    import_sos_shoot(database, TwoSingles(), candidate, 2026)
    observations = database.query(
        """
        SELECT discipline,targets,hits FROM score_observations
        WHERE source='sosclays' ORDER BY discipline
        """
    )
    assert observations == [
        {"discipline": "handicap", "targets": 100, "hits": 93},
        {"discipline": "singles", "targets": 200, "hits": 195},
    ]
