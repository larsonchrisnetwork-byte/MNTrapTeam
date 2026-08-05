from __future__ import annotations
from pathlib import Path
import hashlib,re
from datetime import date,datetime
import pandas as pd
try: import pdfplumber
except Exception: pdfplumber=None
from .matcher import ShooterMatcher
from .season import season_bounds

ALIASES={'ata #':'ata_number','ata number':'ata_number','ata':'ata_number','name':'name','shooter':'name','shooter name':'name','category':'category','state':'state','singles targets':'singles_targets','singles hits':'singles_hits','singles score':'singles_score','singles average':'singles_average','handicap targets':'handicap_targets','handicap hits':'handicap_hits','handicap score':'handicap_score','handicap average':'handicap_average','doubles targets':'doubles_targets','doubles hits':'doubles_hits','doubles score':'doubles_score','doubles average':'doubles_average','mn singles':'mn_singles_targets','mn handicap':'mn_handicap_targets','mn doubles':'mn_doubles_targets','mn clubs':'mn_clubs','haa':'haa_complete','discipline':'discipline','targets':'targets','hits':'hits','score':'score'}
def norm(v):return re.sub(r'[^a-z0-9]+',' ',str(v).strip().lower()).strip()
def number(v,default=0):
    try:
        if pd.isna(v):return default
        return float(str(v).replace('%','').replace(',','').strip())
    except:return default
def truth(v):return str(v).strip().lower() in {'1','yes','true','y','complete','completed'}
def read_table(path):
    path=Path(path); ext=path.suffix.lower()
    if ext=='.csv':return pd.read_csv(path,dtype=str)
    if ext in ('.xlsx','.xlsm'):return pd.read_excel(path,dtype=str)
    if ext in ('.html','.htm'):
        tables=pd.read_html(path.read_text(encoding='utf-8',errors='ignore')); return max(tables,key=len)
    if ext=='.pdf':
        if not pdfplumber:raise RuntimeError('Install pdfplumber for PDF import')
        candidates=[]
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables() or []:
                    if table and len(table)>1:candidates.append(table)
        if not candidates:raise ValueError('No table detected. Save the report as CSV or HTML and import that instead.')
        table=max(candidates,key=len); return pd.DataFrame(table[1:],columns=table[0])
    raise ValueError(f'Unsupported file type: {ext}')
def canonicalize(df):
    out=pd.DataFrame()
    for c in df.columns:
        key=ALIASES.get(norm(c),norm(c).replace(' ','_')); out[key]=df[c]
    return out

class OfficialStatsImporter:
    def __init__(self,db):self.db=db
    def import_file(self,path,season):
        df=canonicalize(read_table(path)); imported=0; warnings=[]
        for idx,r in df.fillna('').iterrows():
            name=str(r.get('name') or '').strip(); ata=str(r.get('ata_number') or '').strip()
            if not name: warnings.append(f'Row {idx+2}: no shooter name'); continue
            cat=str(r.get('category') or 'MEN').strip().upper().replace(' ','_'); sid=self.db.upsert_shooter(ata,name,cat,str(r.get('state') or 'MN'))
            vals={'category_declared':cat,'source':'ShootATA authorized import','official':1,'haa_complete':int(truth(r.get('haa_complete')))}
            for d in ('singles','handicap','doubles'):
                t=int(number(r.get(f'{d}_targets'))); h=int(number(r.get(f'{d}_hits')))
                if not h and t and number(r.get(f'{d}_average')):h=round(t*number(r.get(f'{d}_average'))/100)
                if h>t:warnings.append(f'{name}: {d} hits exceeded targets; row skipped'); h=0;t=0
                vals[f'{d}_targets']=t;vals[f'{d}_hits']=h
            for k in ('mn_singles_targets','mn_handicap_targets','mn_doubles_targets','mn_clubs'):vals[k]=int(number(r.get(k)))
            self.db.upsert_stats(sid,season,**vals); imported+=1
        return imported,warnings

class ScoreboardImporter:
    DISC={'s':'singles','singles':'singles','16':'singles','16s':'singles','h':'handicap','handicap':'handicap','d':'doubles','doubles':'doubles'}
    def __init__(self,db,threshold=88):self.db=db;self.matcher=ShooterMatcher(db,threshold)
    def import_file(self,path,season,shoot_name=None,club='',shoot_date=None,in_state=True):
        path=Path(path);digest=hashlib.sha256(path.read_bytes()).hexdigest()
        if self.db.query('SELECT id FROM imports WHERE sha256=?',(digest,)):return 0,['This exact file was already imported']
        df=canonicalize(read_table(path));shoot_name=shoot_name or path.stem;shoot_date=shoot_date or date.today().isoformat();warnings=[];imported=0
        shoot_id=self.db.execute('INSERT OR IGNORE INTO shoots(name,club,state,start_date,source_type) VALUES(?,?,?,?,?)',(shoot_name,club,'MN' if in_state else '',shoot_date,'ShootScoreBoard'))
        if not shoot_id:shoot_id=self.db.query('SELECT id FROM shoots WHERE name=? AND start_date=? AND club=?',(shoot_name,shoot_date,club))[0]['id']
        for idx,r in df.fillna('').iterrows():
            name=str(r.get('name') or r.get('shooter_name') or '').strip();ata=str(r.get('ata_number') or '').strip()
            if not name:continue
            sid,confidence=self.matcher.match(name,ata)
            if sid is None:sid=self.db.upsert_shooter(ata,name,str(r.get('category') or 'MEN'));warnings.append(f'Created new shooter: {name} (match confidence {confidence:.0f})')
            events=[]
            for d in ('singles','handicap','doubles'):
                t=int(number(r.get(f'{d}_targets')));h=int(number(r.get(f'{d}_hits') or r.get(f'{d}_score')))
                if h and not t:t=100
                if t:events.append((d,t,h))
            if not events and r.get('discipline'):
                d=self.DISC.get(norm(r.get('discipline')));t=int(number(r.get('targets') or 100));h=int(number(r.get('hits') or r.get('score')))
                if d:events=[(d,t,h)]
            for d,t,h in events:
                if not 0<=h<=t:warnings.append(f'{name}: invalid {d} score {h}/{t}');continue
                self.db.execute('INSERT OR REPLACE INTO scores(shooter_id,shoot_id,event_date,event_name,discipline,targets,hits,in_state,club_key,source,official,raw_name) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(sid,shoot_id,shoot_date,shoot_name,d,t,h,int(in_state),club or shoot_name,'ShootScoreBoard',0,name));imported+=1
        self.db.execute('INSERT INTO imports(filename,kind,sha256,rows_read,rows_imported,warnings) VALUES(?,?,?,?,?,?)',(path.name,'scoreboard',digest,len(df),imported,'\n'.join(warnings)))
        self.rebuild_stats(season);return imported,warnings
    def rebuild_stats(self,season):
        start_date, end_date = season_bounds(int(season))
        rows=self.db.query("""SELECT shooter_id,discipline,SUM(targets) targets,SUM(hits) hits,
            SUM(CASE WHEN in_state=1 THEN targets ELSE 0 END) mn_targets
            FROM scores WHERE event_date BETWEEN ? AND ? GROUP BY shooter_id,discipline""",(start_date,end_date))
        clubs={r['shooter_id']:r['clubs'] for r in self.db.query(
            "SELECT shooter_id,COUNT(DISTINCT club_key) clubs FROM scores WHERE in_state=1 AND event_date BETWEEN ? AND ? GROUP BY shooter_id",
            (start_date,end_date))}
        grouped={}
        for r in rows:
            g=grouped.setdefault(r['shooter_id'],{'source':'Score imports','official':0});d=r['discipline']
            g[f'{d}_targets']=r['targets'];g[f'{d}_hits']=r['hits'];g[f'mn_{d}_targets']=r['mn_targets'];g['mn_clubs']=clubs.get(r['shooter_id'],0)
        for sid,v in grouped.items():
            existing=self.db.query('SELECT official FROM season_stats WHERE shooter_id=? AND season=?',(sid,season))
            if existing and existing[0].get('official'):
                # Keep official ATA totals; only supplement MN-specific eligibility fields from score imports.
                v={k:val for k,val in v.items() if k.startswith('mn_')}
                v['source']='Official totals + score-import MN counts'; v['official']=1
            self.db.upsert_stats(sid,season,**v)
