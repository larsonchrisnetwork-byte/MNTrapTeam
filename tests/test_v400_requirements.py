from mntrapteam.eligibility_engine import MEN_OPEN_REQUIREMENTS

def test_requirements():
    assert MEN_OPEN_REQUIREMENTS["total_singles"] == 1500
    assert MEN_OPEN_REQUIREMENTS["total_handicap"] == 1200
    assert MEN_OPEN_REQUIREMENTS["total_doubles"] == 100
    assert MEN_OPEN_REQUIREMENTS["mn_singles"] == 700
    assert MEN_OPEN_REQUIREMENTS["mn_handicap"] == 700
    assert MEN_OPEN_REQUIREMENTS["mn_doubles"] == 700
    assert MEN_OPEN_REQUIREMENTS["mn_clubs"] == 4
