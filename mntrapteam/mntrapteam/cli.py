from __future__ import annotations
import argparse,json
from pathlib import Path
from .database import Database
from .rules import RulesEngine
from .services import TeamService,ExportService
from .importers import OfficialStatsImporter,ScoreboardImporter
from .paths import ROOT,CONFIG

def main(argv=None):
    p=argparse.ArgumentParser(prog='mntrapteam');p.add_argument('--db',default=None)
    sub=p.add_subparsers(dest='cmd',required=True)
    a=sub.add_parser('import-official');a.add_argument('file');a.add_argument('--season',type=int,required=True)
    a=sub.add_parser('import-scoreboard');a.add_argument('file');a.add_argument('--season',type=int,required=True);a.add_argument('--club',required=True);a.add_argument('--date');a.add_argument('--out-of-state',action='store_true')
    a=sub.add_parser('rank');a.add_argument('--season',type=int,required=True);a.add_argument('--team',required=True,choices=['MEN','LADY','VET','SR_VET','JUNIOR','SUB_JR']);a.add_argument('--json',action='store_true')
    a=sub.add_parser('export');a.add_argument('--season',type=int,required=True);a.add_argument('--team');a.add_argument('--format',choices=['csv','xlsx','pdf'],default='xlsx')
    sub.add_parser('backup')
    args=p.parse_args(argv);settings=json.loads((CONFIG/'settings.json').read_text());db=Database(args.db or ROOT/settings['database']);rules=RulesEngine();ts=TeamService(db,rules);ex=ExportService(ts)
    if args.cmd=='import-official':print(OfficialStatsImporter(db).import_file(args.file,args.season))
    elif args.cmd=='import-scoreboard':print(ScoreboardImporter(db).import_file(args.file,args.season,club=args.club,shoot_date=args.date,in_state=not args.out_of_state))
    elif args.cmd=='rank':
        rows=ts.rankings(args.season,args.team)
        if args.json:print(json.dumps(rows,indent=2,default=str))
        else:
            for r in rows:print(f"{r['rank']:>2} {'*' if r['selected'] else ' '} {r['display_name']:<28} {r['hoa']:6.2f} {'ELIG' if r['eligible'] else r['eligibility_reasons']}")
    elif args.cmd=='export':
        if args.format=='xlsx':print(ex.xlsx_all(args.season))
        elif args.format=='csv':print(ex.csv_team(args.season,args.team or 'MEN'))
        else:print(ex.pdf_team(args.season,args.team or 'MEN'))
    elif args.cmd=='backup':print(db.backup())
if __name__=='__main__':main()
