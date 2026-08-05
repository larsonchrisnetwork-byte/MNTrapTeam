
from mntrapteam.ingestion import BatchImportService, TrackedOfficialStatsImporter, classify_file

def official_csv(path):
    path.write_text("ATA Number,Name,Category,Singles Targets,Singles Hits,Handicap Targets,Handicap Hits,Doubles Targets,Doubles Hits\n1234567,Test Shooter,MEN,1500,1450,1200,1080,1000,930\n",encoding="utf-8")

def scoreboard_csv(path):
    path.write_text("ATA Number,Name,Singles Score,Singles Targets\n1234567,Test Shooter,99,100\n",encoding="utf-8")

def test_classification(tmp_path):
    official=tmp_path/"official.csv"; scoreboard=tmp_path/"scoreboard.csv"
    official_csv(official); scoreboard_csv(scoreboard)
    assert classify_file(official)=="official"
    assert classify_file(scoreboard)=="scoreboard"

def test_official_duplicate_tracking(tmp_path,database):
    official=tmp_path/"official.csv"; official_csv(official)
    first=TrackedOfficialStatsImporter(database).import_file(official,2026)
    second=TrackedOfficialStatsImporter(database).import_file(official,2026)
    assert first[0]==1 and second[0]==0
    assert "already imported" in second[1][0].lower()
    assert database.scalar("SELECT COUNT(*) FROM imports")==1

def test_folder_import(tmp_path,database):
    folder=tmp_path/"incoming"; folder.mkdir()
    official_csv(folder/"official.csv"); scoreboard_csv(folder/"scoreboard.csv")
    (folder/"ignored.txt").write_text("ignore",encoding="utf-8")
    results=BatchImportService(database).import_folder(folder,2026,club="Test Club",shoot_date="2026-01-01")
    assert len(results)==2
    assert {r.kind for r in results}=={"official","scoreboard"}
    assert sum(r.rows_imported for r in results)==2

def test_folder_second_run_marks_duplicates(tmp_path,database):
    folder=tmp_path/"incoming"; folder.mkdir(); official_csv(folder/"official.csv")
    service=BatchImportService(database); service.import_folder(folder,2026)
    second=service.import_folder(folder,2026)
    assert second[0].skipped_duplicate is True
