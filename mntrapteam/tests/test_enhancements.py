from mntrapteam.database import Database
from mntrapteam.calculations import projected_hoa, eligibility_completion
from mntrapteam.rules import RulesEngine
from mntrapteam.services import TeamService

def test_projected_hoa():
    row={'singles_hits':95,'singles_targets':100,'handicap_hits':90,'handicap_targets':100,'doubles_hits':85,'doubles_targets':100}
    p=projected_hoa(row,{'doubles':(100,95)})
    assert round(p['averages']['doubles'],2)==90.0
    assert round(p['hoa'],2)==91.67

def test_import_issue_and_diagnostics(tmp_path):
    db=Database(tmp_path/'x.db')
    db.record_import('x.csv','official','abc',1,0,['bad row'])
    d=db.diagnostics()
    assert d['imports']==1 and d['open_import_issues']==1

def test_completion_and_cutline(tmp_path):
    assert eligibility_completion({'x':(5,10),'y':(10,10)})==75
    db=Database(tmp_path/'x.db'); rules=RulesEngine(); ts=TeamService(db,rules)
    for i,avg in enumerate((99,98),1):
        sid=db.upsert_shooter(str(i),f'Shooter {i}','MEN')
        db.upsert_stats(sid,2026,singles_targets=1500,singles_hits=round(1500*avg/100),handicap_targets=1200,handicap_hits=round(1200*avg/100),doubles_targets=1000,doubles_hits=round(1000*avg/100),mn_singles_targets=700,mn_handicap_targets=700,mn_doubles_targets=400,mn_clubs=4,haa_complete=1)
    rows=ts.rankings(2026,'MEN')
    assert rows[0]['cutline_hoa'] is not None
    assert rows[1]['hoa_gap_to_cut']>=0
