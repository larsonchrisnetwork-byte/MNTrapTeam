from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
DATA=ROOT/"data"
EXPORTS=ROOT/"exports"
CONFIG=ROOT/"config"
DOCS=ROOT/"docs"
for p in (DATA, EXPORTS, DATA/"imports", DATA/"backups", DATA/"archives"): p.mkdir(parents=True, exist_ok=True)
