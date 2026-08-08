from mntrapteam.official_baseline import official_through_date_from_detail_rows

def test_latest_date():
    rows = [
        ["1", "07/01/2026", "A", "B"],
        ["2", "08/03/2026", "C", "D"],
        ["3", "07/28/2026", "E", "F"],
    ]
    assert official_through_date_from_detail_rows(rows) == "2026-08-03"
