import json

from mntrapteam.myata_capture import (
    extract_myata_payloads,
    normalize_myata_detail_rows,
)


def test_extracts_member_and_current_year_details(tmp_path):
    payload = [
        {
            "url": "https://shootata.com/API/GetMemberInfo",
            "body": {
                "AtaNumber": "0113918",
                "MemberName": "CHRIS LARSON",
            },
        },
        {
            "url": (
                "https://shootata.com/API/GetMemberStatsDetails?"
                "ataNumber=0113918&year=2026"
            ),
            "body": {
                "MemberPerformanceInfos": [
                    {
                        "ShootNumber": "4359",
                        "Date": "7/19/2026",
                        "Name": "BUFFALO GUN CLUB",
                        "SinglesShot": 0,
                        "SinglesHit": 0,
                        "HandicapShot": 0,
                        "HandicapHit": 0,
                        "DoublesShot": 100,
                        "DoublesHit": 97,
                    }
                ]
            },
        },
    ]
    path = tmp_path / "network_json.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    member, details, warnings = extract_myata_payloads(path, 2026)
    assert member["AtaNumber"] == "0113918"
    assert len(details) == 1
    assert warnings == []


def test_normalizes_and_skips_administrative_rows():
    rows = [
        {
            "Date": "9/1/2025",
            "Name": "Change of category by ATA office",
            "SinglesShot": 0,
            "HandicapShot": 0,
            "DoublesShot": 0,
        },
        {
            "Date": "7/4/2026",
            "Name": "MINNESOTA TRAP ASSN",
            "SinglesShot": 200,
            "SinglesHit": 190,
            "HandicapShot": 0,
            "DoublesShot": 0,
        },
    ]
    normalized = normalize_myata_detail_rows(rows)
    assert len(normalized) == 1
    assert normalized[0]["Date"] == "2026-07-04"
    assert normalized[0]["Name"] == "MINNESOTA STATE SHOOT"
    assert normalized[0]["State"] == "MN"
