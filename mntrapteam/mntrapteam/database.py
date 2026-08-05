from __future__ import annotations
import sqlite3, shutil, json
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from .paths import DATA

SCHEMA=r"""
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS schema_version(version INTEGER NOT NULL);
INSERT INTO schema_version SELECT 2 WHERE NOT EXISTS(SELECT 1 FROM schema_version);
CREATE TABLE IF NOT EXISTS shooters(id INTEGER PRIMARY KEY,ata_number TEXT UNIQUE,first_name TEXT,last_name TEXT,display_name TEXT NOT NULL,state TEXT DEFAULT 'MN',category TEXT DEFAULT 'MEN',yardage REAL,active INTEGER DEFAULT 1,created_at TEXT DEFAULT CURRENT_TIMESTAMP,updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS season_stats(id INTEGER PRIMARY KEY,shooter_id INTEGER NOT NULL,season INTEGER NOT NULL,singles_targets INTEGER DEFAULT 0,singles_hits INTEGER DEFAULT 0,handicap_targets INTEGER DEFAULT 0,handicap_hits INTEGER DEFAULT 0,doubles_targets INTEGER DEFAULT 0,doubles_hits INTEGER DEFAULT 0,mn_singles_targets INTEGER DEFAULT 0,mn_handicap_targets INTEGER DEFAULT 0,mn_doubles_targets INTEGER DEFAULT 0,mn_clubs INTEGER DEFAULT 0,haa_complete INTEGER DEFAULT 0,category_declared TEXT,source TEXT DEFAULT 'manual',official INTEGER DEFAULT 0,updated_at TEXT DEFAULT CURRENT_TIMESTAMP,UNIQUE(shooter_id,season),FOREIGN KEY(shooter_id) REFERENCES shooters(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS shoots(id INTEGER PRIMARY KEY,name TEXT NOT NULL,club TEXT,city TEXT,state TEXT,start_date TEXT,end_date TEXT,source_url TEXT,source_type TEXT,imported_at TEXT DEFAULT CURRENT_TIMESTAMP,UNIQUE(name,start_date,club));
CREATE TABLE IF NOT EXISTS scores(id INTEGER PRIMARY KEY,shooter_id INTEGER NOT NULL,shoot_id INTEGER,event_date TEXT,event_name TEXT,discipline TEXT NOT NULL CHECK(discipline IN ('singles','handicap','doubles')),targets INTEGER NOT NULL CHECK(targets>=0),hits INTEGER NOT NULL CHECK(hits>=0 AND hits<=targets),in_state INTEGER DEFAULT 0,club_key TEXT,source TEXT,official INTEGER DEFAULT 0,raw_name TEXT,UNIQUE(shooter_id,shoot_id,event_name,discipline),FOREIGN KEY(shooter_id) REFERENCES shooters(id) ON DELETE CASCADE,FOREIGN KEY(shoot_id) REFERENCES shoots(id) ON DELETE SET NULL);
CREATE TABLE IF NOT EXISTS imports(id INTEGER PRIMARY KEY,filename TEXT,kind TEXT,sha256 TEXT UNIQUE,rows_read INTEGER DEFAULT 0,rows_imported INTEGER DEFAULT 0,warnings TEXT,imported_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS aliases(id INTEGER PRIMARY KEY,raw_name TEXT UNIQUE,shooter_id INTEGER NOT NULL,confidence REAL,FOREIGN KEY(shooter_id) REFERENCES shooters(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS snapshots(id INTEGER PRIMARY KEY,season INTEGER,label TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP,payload TEXT);
CREATE INDEX IF NOT EXISTS idx_stats_season ON season_stats(season); CREATE INDEX IF NOT EXISTS idx_scores_shooter ON scores(shooter_id); CREATE INDEX IF NOT EXISTS idx_scores_date ON scores(event_date);
"""
class Database:
    def __init__(self,path): self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True); self.initialize()
    @contextmanager
    def connect(self):
        con=sqlite3.connect(self.path); con.row_factory=sqlite3.Row; con.execute('PRAGMA foreign_keys=ON'); con.execute('PRAGMA journal_mode=WAL')
        try: yield con; con.commit()
        except: con.rollback(); raise
        finally: con.close()
    def initialize(self):
        with self.connect() as con: con.executescript(SCHEMA)
    def execute(self,sql,params=()):
        with self.connect() as con: return con.execute(sql,params).lastrowid
    def query(self,sql,params=()):
        with self.connect() as con: return [dict(r) for r in con.execute(sql,params).fetchall()]
    def scalar(self,sql,params=(),default=None):
        rows=self.query(sql,params); return next(iter(rows[0].values())) if rows else default
    def upsert_shooter(self,ata_number,display_name,category='MEN',state='MN',yardage=None):
        ata=''.join(ch for ch in str(ata_number or '') if ch.isdigit()) or None; name=' '.join(str(display_name).split()); parts=name.split(); first=parts[0] if parts else ''; last=' '.join(parts[1:]) if len(parts)>1 else ''
        with self.connect() as con:
            if ata:
                con.execute("INSERT INTO shooters(ata_number,first_name,last_name,display_name,state,category,yardage) VALUES(?,?,?,?,?,?,?) ON CONFLICT(ata_number) DO UPDATE SET display_name=excluded.display_name,first_name=excluded.first_name,last_name=excluded.last_name,state=excluded.state,category=excluded.category,yardage=COALESCE(excluded.yardage,shooters.yardage),updated_at=CURRENT_TIMESTAMP",(ata,first,last,name,state.upper(),category,yardage))
                return con.execute('SELECT id FROM shooters WHERE ata_number=?',(ata,)).fetchone()[0]
            row=con.execute('SELECT id FROM shooters WHERE upper(display_name)=upper(?)',(name,)).fetchone()
            if row:return row[0]
            return con.execute('INSERT INTO shooters(first_name,last_name,display_name,state,category,yardage) VALUES(?,?,?,?,?,?)',(first,last,name,state.upper(),category,yardage)).lastrowid
    def upsert_stats(self,shooter_id,season,**values):
        allowed={'singles_targets','singles_hits','handicap_targets','handicap_hits','doubles_targets','doubles_hits','mn_singles_targets','mn_handicap_targets','mn_doubles_targets','mn_clubs','haa_complete','category_declared','source','official'}; data={k:v for k,v in values.items() if k in allowed}
        with self.connect() as con:
            con.execute('INSERT INTO season_stats(shooter_id,season) VALUES(?,?) ON CONFLICT(shooter_id,season) DO NOTHING',(shooter_id,season))
            if data: con.execute('UPDATE season_stats SET '+','.join(f'{k}=?' for k in data)+',updated_at=CURRENT_TIMESTAMP WHERE shooter_id=? AND season=?',(*data.values(),shooter_id,season))
    def backup(self):
        dest=DATA/'backups'/f"mntrapteam_{datetime.now():%Y%m%d_%H%M%S}.db"; dest.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(self.path) as source,sqlite3.connect(dest) as target: source.backup(target)
        return dest
    def restore(self,backup_path):
        backup_path=Path(backup_path)
        if not backup_path.exists():raise FileNotFoundError(backup_path)
        safety=self.backup(); shutil.copy2(backup_path,self.path); self.initialize(); return safety
