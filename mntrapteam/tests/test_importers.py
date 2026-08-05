from pathlib import Path
from mntrapteam.database import Database
from mntrapteam.importers import OfficialStatsImporter,ScoreboardImporter

def test_official_import(tmp_path):
    db=Database(tmp_path/'x.db');f=tmp_path/'o.csv';f.write_text('ATA Number,Name,Category,Singles Targets,Singles Hits,Handicap Targets,Handicap Hits,Doubles Targets,Doubles Hits,MN Singles,MN Handicap,MN Doubles,MN Clubs,HAA\n1234567,Test Shooter,MEN,1500,1450,1200,1080,1000,930,700,700,400,4,yes\n')
    n,w=OfficialStatsImporter(db).import_file(f,2026);assert n==1 and not w;assert db.scalar('select count(*) from season_stats')==1

def test_scoreboard_import(tmp_path):
    db=Database(tmp_path/'x.db');f=tmp_path/'s.csv';f.write_text('ATA Number,Name,Singles Score,Singles Targets\n1234567,Test Shooter,99,100\n')
    n,w=ScoreboardImporter(db).import_file(f,2026,club='Test Club',shoot_date='2026-01-01');assert n==1;assert db.scalar('select count(*) from scores')==1
