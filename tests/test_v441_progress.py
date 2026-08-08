from pathlib import Path

def test_progress_and_timeouts_present():
    text = Path("mntrapteam/recent_score_scout_cli.py").read_text(encoding="utf-8")
    assert "Discovery {index}/{len(ids)}" in text
    assert "timeout=4" in text
    assert "timeout=5" in text
    assert "no browser login is required" in text
