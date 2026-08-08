from mntrapteam.rules import RulesEngine

def test_state_team_category_aliases():
    rules = RulesEngine()
    assert rules.team_for_category("SBV") == "MEN"
    assert rules.team_for_category("L1") == "LADY"
    assert rules.team_for_category("L2") == "LADY"
    assert rules.team_for_category("V") == "VET"
    assert rules.team_for_category("SRV") == "SR_VET"
    assert rules.team_for_category("J") == "JUNIOR"
    assert rules.team_for_category("SJ") == "SUB_JR"
