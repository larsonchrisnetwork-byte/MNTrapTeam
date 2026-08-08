from mntrapteam.myata_mn_enrichment import (
    SOSClubDirectory,
    enrich_score_detail_rows,
)


def test_exact_mn_club_counts_targets_and_club():
    directory = SOSClubDirectory([
        {"clubId": 1, "name": "Del-Tone Shooting Range", "stateProvince": "MN"},
        {"clubId": 2, "name": "Some Iowa Gun Club", "stateProvince": "IA"},
    ])

    rows = [
        ["1","5/1/2026","Del-Tone Shooting Range","100","95","","","20","","100","90","","100","92","",""],
        ["2","5/2/2026","Some Iowa Gun Club","100","99","","","27","","100","95","","100","98","",""],
    ]

    totals = enrich_score_detail_rows(rows, directory)

    assert totals.singles_targets == 100
    assert totals.handicap_targets == 100
    assert totals.doubles_targets == 100
    assert totals.mn_clubs == 1


def test_assn_normalizes_to_association():
    directory = SOSClubDirectory([
        {"clubId": 10, "name": "Minnesota Trap Association", "stateProvince": "MN"},
    ])

    match = directory.match("MINNESOTA TRAP ASSN")
    assert match.confident
    assert match.is_minnesota
