from mntrapteam.database import Database
from mntrapteam.importers import ScoreboardImporter

def test_rebuild_filters_season_and_preserves_official(tmp_path):
    db=Database(tmp_path/'x.db')
    sid=db.upsert_shooter('123','Test Shooter')
    shoot1=db.execute("INSERT INTO shoots(name,start_date) VALUES(?,?)",('old','2024-01-01'))
    shoot2=db.execute("INSERT INTO shoots(name,start_date) VALUES(?,?)",('new','2026-01-01'))
    db.execute("INSERT INTO scores(shooter_id,shoot_id,event_date,event_name,discipline,targets,hits,in_state,club_key) VALUES(?,?,?,?,?,?,?,?,?)",(sid,shoot1,'2024-01-01','old','singles',100,90,1,'A'))
    db.execute("INSERT INTO scores(shooter_id,shoot_id,event_date,event_name,discipline,targets,hits,in_state,club_key) VALUES(?,?,?,?,?,?,?,?,?)",(sid,shoot2,'2026-01-01','new','singles',100,95,1,'B'))
    db.upsert_stats(sid,2026,singles_targets=2000,singles_hits=1900,official=1,source='official')
    ScoreboardImporter(db).rebuild_stats(2026)
    row=db.query('SELECT * FROM season_stats WHERE shooter_id=? AND season=?',(sid,2026))[0]
    assert row['singles_targets']==2000
    assert row['singles_hits']==1900
    assert row['mn_singles_targets']==100
    assert row['official']==1
