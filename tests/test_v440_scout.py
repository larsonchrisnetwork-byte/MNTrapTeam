from mntrapteam.recent_score_scout_cli import _compact_name, _name_keys

def test_name_matching_variants():
    keys = _name_keys("CHRISTOPHER W. LARSON", "Christopher", "Larson")
    assert "CHRISTOPHER LARSON" in keys
    assert "LARSON CHRISTOPHER" in keys
    assert _compact_name("Larson, Christopher") == "LARSON CHRISTOPHER"
