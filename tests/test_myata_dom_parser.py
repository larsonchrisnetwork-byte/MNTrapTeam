from mntrapteam.myata_dom_parser import (
    parse_score_detail_rows,
    parse_year_summary_row,
    validate_detail_against_summary,
)


def test_aiden_summary_row():
    cells = [
        "2026", "1000", "91.10%", "", "",
        "800", "85.88%", "400", "67.00%", "", ""
    ]
    row = parse_year_summary_row(cells)
    assert row["singles_targets"] == 1000
    assert row["handicap_targets"] == 800
    assert row["doubles_targets"] == 400


def test_aiden_detail_targets_and_hits():
    rows = [
        ["0116","9/7/2025","Del-Tone","100","93","","","20","","100","83","","","","",""],
        ["1534","1/4/2026","Del-Tone","100","80","","","","","","","","","","","",""],
        ["1974","3/8/2026","Del-Tone","100","91","","","","","","","","","","","",""],
        ["2980","5/9/2026","MYSA","100","89","","","20","","100","82","","","","",""],
        ["3171","5/10/2026","Alexandria","100","91","","","20","","100","80","","100","61","",""],
        ["2985","5/16/2026","MYSA","100","91","","","20","","100","84","","","","",""],
        ["3505","5/31/2026","Del-Tone","100","94","","","20","","100","83","","100","69","",""],
        ["4257","7/3/2026","MTA","","","","","20","","100","92","","100","76","",""],
        ["4257","7/4/2026","MTA","200","188","","","","","","","","","","","",""],
        ["4257","7/5/2026","MTA","","","","","20","","100","89","","","","",""],
        ["4528","7/18/2026","Del-Tone","100","94","","","20","","100","94","","100","62","",""],
    ]
    totals = parse_score_detail_rows(rows)
    assert totals.singles_targets == 1000
    assert totals.singles_hits == 911
    assert totals.handicap_targets == 800
    assert totals.handicap_hits == 687
    assert totals.doubles_targets == 400
    assert totals.doubles_hits == 268


def test_aiden_detail_reconciles_to_summary():
    summary = parse_year_summary_row(
        ["2026","1000","91.10%","","","800","85.88%","400","67.00%","",""]
    )
    totals = parse_score_detail_rows([
        ["1","1/1/2026","A","1000","911","","","20","","800","687","","400","268","",""]
    ])
    assert validate_detail_against_summary(totals, summary) == []
