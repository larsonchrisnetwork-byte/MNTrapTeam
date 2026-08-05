from __future__ import annotations
import sqlite3, json, shutil
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from .paths import ROOT, DATA

SCHEMA = r"""
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS shooters(
 id INTEGER PRIMARY KEY, ata_number TEXT UNIQUE, first_name TEXT, last_name TEXT, display_name TEXT NOT NULL,
 state TEXT DEFAULT 'MN', category TEXT DEFAULT 'MEN', yardage REAL, active INTEGER DEFAULT 1,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS seasons(id INTEGER PRIMARY KEY, year INTEGER UNIQUE NOT NULL, start_date TEXT, end_date TEXT, locked INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS season_stats(
 id INTEGER PRIMARY KEY, shooter_id INTEGER NOT NULL, season INTEGER NOT NULL,
 singles_targets INTEGER DEFAULT 0, singles_hits INTEGER DEFAULT 0,
 handicap_targets INTEGER DEFAULT 0, handicap_hits INTEGER DEFAULT 0,
 doubles_targets INTEGER DEFAULT 0, doubles_hits INTEGER DEFAULT 0,
 mn_singles_targets INTEGER DEFAULT 0, mn_handicap_targets INTEGER DEFAULT 0, mn_doubles_targets INTEGER DEFAULT 0,
 mn_clubs INTEGER DEFAULT 0, haa_complete INTEGER DEFAULT 0, category_declared TEXT,
 source TEXT DEFAULT 'manual', official INTEGER DEFAULT 0, updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
 UNIQUE(shooter_id, season), FOREIGN KEY(shooter_id) REFERENCES shooters(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS shoots(id INTEGER PRIMARY KEY, name TEXT, club TEXT, city TEXT, state TEXT, start_date TEXT, end_date TEXT, source_url TEXT, source_type TEXT, imported_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(name,start_date,club));
CREATE TABLE IF NOT EXISTS scores(
 id INTEGER PRIMARY KEY, shooter_id INTEGER NOT NULL, shoot_id INTEGER, event_date TEXT, event_name TEXT,
 discipline TEXT NOT NULL, targets INTEGER NOT NULL, hits INTEGER NOT NULL, in_state INTEGER DEFAULT 0,
 club_key TEXT, source TEXT, official INTEGER DEFAULT 0, raw_name TEXT,
 UNIQUE(shooter_id,shoot_id,event_name,discipline), FOREIGN KEY(shooter_id) REFERENCES shooters(id) ON DELETE CASCADE, FOREIGN KEY(shoot_id) REFERENCES shoots(id) ON DELETE SET NULL);
CREATE TABLE IF NOT EXISTS imports(id INTEGER PRIMARY KEY, filename TEXT, kind TEXT, sha256 TEXT UNIQUE, rows_read INTEGER DEFAULT 0, rows_imported INTEGER DEFAULT 0, warnings TEXT, imported_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS aliases(id INTEGER PRIMARY KEY, raw_name TEXT UNIQUE, shooter_id INTEGER NOT NULL, confidence REAL, FOREIGN KEY(shooter_id) REFERENCES shooters(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS snapshots(id INTEGER PRIMARY KEY, season INTEGER, label TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, payload TEXT);
CREATE INDEX IF NOT EXISTS idx_stats_season ON season_stats(season);
CREATE INDEX IF NOT EXISTS idx_scores_shooter ON scores(shooter_id);
"""

class Database:
    def __init__(self, path: str|Path): self.path=Path(path); self.path.parent.mkdir(parents=True, exist_ok=True); self.initialize()
    @contextmanager
    def connect(self):
        con=sqlite3.connect(self.path); con.row_factory=sqlite3.Row; con.execute('PRAGMA foreign_keys=ON')
        try: yield con; con.commit()
        finally: con.close()
    def initialize(self):
        with self.connect() as con: con.executescript(SCHEMA)
    def execute(self, sql, params=()):
        with self.connect() as con: return con.execute(sql, params).lastrowid
    def query(self, sql, params=()):
        with self.connect() as con: return [dict(r) for r in con.execute(sql, params).fetchall()]
    def upsert_shooter(self, ata_number, display_name, category='MEN', state='MN', yardage=None):
        ata=(ata_number or '').strip() or None; parts=display_name.strip().split(); first=parts[0] if parts else ''; last=' '.join(parts[1:]) if len(parts)>1 else ''
        with self.connect() as con:
            if ata:
                con.execute("INSERT INTO shooters(ata_number,first_name,last_name,display_name,state,category,yardage) VALUES(?,?,?,?,?,?,?) ON CONFLICT(ata_number) DO UPDATE SET display_name=excluded.display_name,first_name=excluded.first_name,last_name=excluded.last_name,state=excluded.state,category=excluded.category,yardage=COALESCE(excluded.yardage,shooters.yardage),updated_at=CURRENT_TIMESTAMP",(ata,first,last,display_name,state,category,yardage))
                return con.execute('SELECT id FROM shooters WHERE ata_number=?',(ata,)).fetchone()[0]
            row=con.execute('SELECT id FROM shooters WHERE upper(display_name)=upper(?)',(display_name,)).fetchone()
            if row: return row[0]
            return con.execute('INSERT INTO shooters(first_name,last_name,display_name,state,category,yardage) VALUES(?,?,?,?,?,?)',(first,last,display_name,state,category,yardage)).lastrowid
    def upsert_stats(self, shooter_id, season, **v):
        cols=['singles_targets','singles_hits','handicap_targets','handicap_hits','doubles_targets','doubles_hits','mn_singles_targets','mn_handicap_targets','mn_doubles_targets','mn_clubs','haa_complete','category_declared','source','official']
        data={k:v[k] for k in cols if k in v}
        with self.connect() as con:
            con.execute('INSERT INTO season_stats(shooter_id,season) VALUES(?,?) ON CONFLICT(shooter_id,season) DO NOTHING',(shooter_id,season))
            if data:
                setsql=', '.join(f'{k}=?' for k in data)+', updated_at=CURRENT_TIMESTAMP'
                con.execute(f'UPDATE season_stats SET {setsql} WHERE shooter_id=? AND season=?',(*data.values(),shooter_id,season))
    def backup(self):
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S'); dest=DATA/'backups'/f'mntrapteam_{stamp}.db'; shutil.copy2(self.path,dest); return dest
