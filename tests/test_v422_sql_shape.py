from pathlib import Path

def test_baseline_insert_value_count():
    text = Path("mntrapteam/official_baseline.py").read_text(encoding="utf-8")
    assert "VALUES(?,?,CURRENT_TIMESTAMP,?,?,?,?,?,?,?,?)" in text
