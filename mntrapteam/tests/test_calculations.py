from mntrapteam.calculations import average,hoa,project,targets_needed_for_average

def test_average_and_hoa():
    assert average(95,100)==95
    assert hoa({'singles_hits':95,'singles_targets':100,'handicap_hits':90,'handicap_targets':100,'doubles_hits':85,'doubles_targets':100})==90

def test_project():
    p=project(950,1000,100,97);assert p['hits']==1047 and p['targets']==1100

def test_needed():
    assert targets_needed_for_average(9495,10000,96,97)==10500
    assert targets_needed_for_average(95,100,96,96) is None
