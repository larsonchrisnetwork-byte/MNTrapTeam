from mntrapteam.sos_native import (
    classify_shoot,
    find_minnesota_haa_shoots,
    shoots_from_list_payload,
)


def test_classify_minnesota_shoots():
    assert classify_shoot(
        "2026 Minnesota Southern Zone"
    ) == ("ZONE", "SOUTHERN")
    assert classify_shoot(
        "2026 Minnesota Northern Zone Shoot"
    ) == ("ZONE", "NORTHERN")
    assert classify_shoot(
        "2026 Minnesota State Shoot"
    ) == ("STATE", "")


def test_shoot_list_parser():
    payload = [
        {
            "name": "2026 Minnesota Southern Zone",
            "shootId": 111,
            "startDate": "6/20/2026",
            "endDate": "6/21/2026",
            "locations": [],
        },
        {
            "name": "2026 Minnesota State Shoot",
            "shootId": 222,
            "startDate": "6/30/2026",
            "endDate": "7/5/2026",
            "locations": [],
        },
    ]

    shoots = shoots_from_list_payload(payload)
    assert len(shoots) == 2
    assert shoots[0].shoot_id == 111
    assert shoots[0].start_date == "2026-06-20"


def test_find_haa_shoots():
    payload = [
        {
            "name": "2026 Minnesota Southern Zone",
            "shootId": 111,
            "startDate": "6/20/2026",
            "endDate": "6/21/2026",
            "locations": [],
        },
        {
            "name": "2026 Minnesota State Shoot",
            "shootId": 222,
            "startDate": "6/30/2026",
            "endDate": "7/5/2026",
            "locations": [],
        },
    ]

    shoots = shoots_from_list_payload(payload)
    found = find_minnesota_haa_shoots(shoots, 2026)
    assert [shoot.shoot_id for shoot in found] == [111, 222]
