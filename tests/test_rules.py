from mntrapteam.rules import RulesEngine

def test_men_requirements():
    r=RulesEngine(); row=dict(category='MEN',state='MN',singles_targets=1500,handicap_targets=1200,doubles_targets=1000,mn_singles_targets=700,mn_handicap_targets=700,mn_doubles_targets=400,mn_clubs=4,haa_complete=1)
    assert r.check(row).eligible
    row['doubles_targets']=999
    assert not r.check(row).eligible

def test_sub_jr_exemptions():
    r=RulesEngine(); row=dict(category='SUB_JR',state='MN',singles_targets=1000,handicap_targets=800,doubles_targets=0,mn_singles_targets=700,mn_handicap_targets=700,mn_doubles_targets=0,mn_clubs=0,haa_complete=1)
    assert r.check(row).eligible
