from mntrapteam.sos_state_haa import validate_state_haa_report


def test_valid_state_haa_event_definition():
    payload = {
        "eventsData": [
            {
                "eventId": 1,
                "eventTypeId": 2,
                "targetQuantity": 100,
                "haaEvent": 1,
            },
            {
                "eventId": 2,
                "eventTypeId": 1,
                "targetQuantity": 200,
                "haaEvent": 1,
            },
            {
                "eventId": 3,
                "eventTypeId": 3,
                "targetQuantity": 100,
                "haaEvent": 1,
            },
            {
                "eventId": 4,
                "eventTypeId": 1,
                "targetQuantity": 100,
                "haaEvent": 0,
            },
        ]
    }
    validate_state_haa_report(payload)


def test_wrong_haa_target_total_rejected():
    payload = {
        "eventsData": [
            {"eventTypeId": 2, "targetQuantity": 100, "haaEvent": 1},
            {"eventTypeId": 1, "targetQuantity": 100, "haaEvent": 1},
            {"eventTypeId": 3, "targetQuantity": 100, "haaEvent": 1},
        ]
    }

    try:
        validate_state_haa_report(payload)
    except ValueError as exc:
        assert "400" in str(exc)
    else:
        raise AssertionError("Expected invalid HAA report to be rejected")
