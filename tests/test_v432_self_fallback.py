from pathlib import Path

def test_self_fallback_present():
    text = Path("mntrapteam/myata_bulk_dom_cli.py").read_text(encoding="utf-8")
    assert "falling back to Search/Buddies" in text
    assert "Self fallback Search/Buddies result was not opened" in text
