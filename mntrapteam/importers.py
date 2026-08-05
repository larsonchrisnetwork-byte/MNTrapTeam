from __future__ import annotations
from pathlib import Path
import csv, hashlib, re
from datetime import date
from bs4 import BeautifulSoup
import pandas as pd
try: import pdfplumber
except Exception: pdfplumber=None
from .matcher import ShooterMatcher

ALIASES={'ata #':'ata_number','ata number':'ata_number','ata':'ata_number','name':'name','shooter':'name','shooter name':'name','category':'category','state':'state','singles targets':'singles_targets','singles hits':'singles_hits','singles average':'singles_average','handicap targets':'handicap_targets','handicap hits':'handicap_hits','handicap average':'handicap_average','doubles targets':'doubles_targets','doubles hits':'doubles_hits','doubles average':'doubles_average','mn singles':'mn_singles_targets','mn handicap':'mn_handicap_targets','mn doubles':'mn_doubles_targets','mn clubs':'mn_clubs','haa':'haa_complete'}

def _norm(s): return re.sub(r'[^a-z0-9]+',' ',str(s).strip().lower()).strip()
def _number(v,default=0):
    try: return float(str(v).replace('%','').replace(',','').strip())
    except: return default

def read_table(path:Path):
    ext=path.suffix.lower()
    if ext=='.csv': return pd.read_csv(path)
    if ext in ('.xlsx','.xlsm'): return pd.read_excel(path)
    if ext in ('.html','.htm'):
        tables=pd.read_html(path.read_text(encoding='utf-8',errors='ignore')); return max(tables,key=len)
    if ext=='.pdf':
        if not pdfplumber: raise RuntimeError('pdfplumber is required for PDF imports')
        rows=[]
        with pdfplumber.open(path) as pdf:
            for pg in pdf.pages:
                for table in pg.extract_tables() or []:
                    if table and len(table)>1: rows.extend(table)
        if not rows: raise ValueError('No table was detected in the PDF')
        return pd.DataFrame(rows[1:],columns=rows[0])
    raise ValueError(f'Unsupported file type: {ext}')

def canonicalize(df):
    out=pd.DataFrame()
    for c in df.columns:
        n=_norm(c); key=ALIASES.get(n,n.replace(' ','_')); out[key]=df[c]
    return out

class OfficialStatsImporter:
    def __init__(self,db): self.db=db
    def import_file(self,path,season):
        df=canonicalize(read_table(Path(path))); imported=0; warnings=[]
        for _,r in df.fillna('').iterrows():
            name=str(r.get('name') or '').strip(); ata=str(r.get('ata_number') or '').strip()
            if not name: warnings.append('Skipped row without shooter name'); continue
            cat=str(r.get('category') or 'MEN').strip().upper().replace(' ','_')
            sid=self.db.upsert_shooter(ata,name,cat,str(r.get('state') or 'MN'))
            vals={'category_declared':cat,'source':'ShootATA import','official':1}
            for d in ('singles','handicap','doubles'):
                t=int(_number(r.get(f'{d}_targets'))); h=int(_number(r.get(f'{d}_hits')))
                if not h and t and _number(r.get(f'{d}_average')): h=round(t*_number(r.get(f'{d}_average'))/100)
                vals[f'{d}_targets']=t; vals[f'{d}_hits']=h
            for k in ('mn_singles_targets','mn_handicap_targets','mn_doubles_targets','mn_clubs'): vals[k]=int(_number(r.get(k)))
            vals['haa_complete']=1 if str(r.get('haa_complete')).strip().lower() in ('1','yes','true','y','complete') else 0
            self.db.upsert_stats(sid,season,**vals); imported+=1
        return imported,warnings

class ScoreboardImporter:
    DISC={'s':'singles','singles':'singles','16':'singles','16s':'singles','h':'handicap','handicap':'handicap','d':'doubles','doubles':'doubles'}
    def __init__(self,db,threshold=88): self.db=db; self.matcher=ShooterMatcher(db,threshold)
    def import_file(self,path,season,shoot_name=None,club='',shoot_date=None,in_state=True):
        path=Path(path); digest=hashlib.sha256(path.read_bytes()).hexdigest()
        if self.db.query('SELECT id FROM imports WHERE sha256=?',(digest,)): return 0,['This file was already imported']
        df=canonicalize(read_table(path)); imported=0; warnings=[]; shoot_name=shoot_name or path.stem; shoot_date=shoot_date or date.today().isoformat()
        shoot_id=self.db.execute('INSERT OR IGNORE INTO shoots(name,club,state,start_date,source_type) VALUES(?,?,?,?,?)',(shoot_name,club,'MN' if in_state else '',shoot_date,'ShootScoreBoard'))
        if not shoot_id:
            shoot_id=self.db.query('SELECT id FROM shoots WHERE name=? AND start_date=? AND club=?',(shoot_name,shoot_date,club))[0]['id']
        for _,r in df.fillna('').iterrows():
            name=str(r.get('name') or r.get('shooter_name') or '').strip(); ata=str(r.get('ata_number') or '').strip()
            if not name: continue
            sid,conf=self.matcher.match(name,ata)
            if sid is None: sid=self.db.upsert_shooter(ata,name,str(r.get('category') or 'MEN')); warnings.append(f'Created shooter {name} (no confident match)')
            # wide format
            events=[]
            for d in ('singles','handicap','doubles'):
                hits=int(_number(r.get(f'{d}_hits') or r.get(f'{d}_score'))); targets=int(_number(r.get(f'{d}_targets')))
                if hits and not targets: targets=100
                if targets: events.append((d,targets,hits))
            # long format
            if not events and r.get('discipline'):
                d=self.DISC.get(_norm(r.get('discipline')),_norm(r.get('discipline'))); targets=int(_number(r.get('targets') or 100)); hits=int(_number(r.get('hits') or r.get('score'))); events=[(d,targets,hits)]
            for d,t,h in events:
                self.db.execute("INSERT OR REPLACE INTO scores(shooter_id,shoot_id,event_date,event_name,discipline,targets,hits,in_state,club_key,source,official,raw_name) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(sid,shoot_id,shoot_date,shoot_name,d,t,h,1 if in_state else 0,club or shoot_name,'ShootScoreBoard',0,name)); imported+=1
        self.db.execute('INSERT INTO imports(filename,kind,sha256,rows_read,rows_imported,warnings) VALUES(?,?,?,?,?,?)',(path.name,'scoreboard',digest,len(df),imported,'\n'.join(warnings)))
        self.rebuild_stats(season)
        return imported,warnings
    def rebuild_stats(self,season):
        rows=self.db.query("SELECT shooter_id,discipline,SUM(targets) targets,SUM(hits) hits,SUM(CASE WHEN in_state=1 THEN targets ELSE 0 END) mn_targets,COUNT(DISTINCT CASE WHEN in_state=1 THEN club_key END) clubs FROM scores GROUP BY shooter_id,discipline")
        grouped={}
        for r in rows:
            g=grouped.setdefault(r['shooter_id'],{'mn_clubs':0,'source':'Score imports','official':0}); d=r['discipline']; g[f'{d}_targets']=r['targets']; g[f'{d}_hits']=r['hits']; g[f'mn_{d}_targets']=r['mn_targets']; g['mn_clubs']=max(g['mn_clubs'],r['clubs'])
        for sid,v in grouped.items(): self.db.upsert_stats(sid,season,**v)
