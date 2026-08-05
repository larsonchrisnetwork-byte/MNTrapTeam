from pathlib import Path
import csv, json, webbrowser
from datetime import datetime
from .calculations import team_rankings, hoa, project
from .paths import EXPORTS

class TeamService:
    def __init__(self,db,rules): self.db=db; self.rules=rules
    def season_rows(self,season):
        rows=self.db.query("SELECT s.*,st.* FROM shooters s JOIN season_stats st ON st.shooter_id=s.id WHERE st.season=? AND s.active=1",(season,))
        for r in rows: r['hoa']=hoa(r); r['eligibility']=self.rules.check(r)
        return rows
    def rankings(self,season,team): return team_rankings(self.season_rows(season),self.rules,team)
    def snapshot(self,season,label):
        payload={t:self.rankings(season,t) for t in self.rules.rules['teams']}
        self.db.execute('INSERT INTO snapshots(season,label,payload) VALUES(?,?,?)',(season,label,json.dumps(payload,default=lambda o:o.__dict__)))

class ExportService:
    def __init__(self,team_service): self.ts=team_service
    def csv_team(self,season,team):
        path=EXPORTS/f'{season}_{team}_standings.csv'; rows=self.ts.rankings(season,team)
        keys=['rank','selected','eligible','display_name','ata_number','category','hoa','singles_targets','handicap_targets','doubles_targets','mn_singles_targets','mn_handicap_targets','mn_doubles_targets','mn_clubs','eligibility_reasons']
        with path.open('w',newline='',encoding='utf-8-sig') as f:
            w=csv.DictWriter(f,fieldnames=keys,extrasaction='ignore'); w.writeheader(); w.writerows(rows)
        return path
    def xlsx_all(self,season):
        import pandas as pd
        path=EXPORTS/f'{season}_MN_State_Teams.xlsx'
        with pd.ExcelWriter(path,engine='openpyxl') as x:
            for team in self.ts.rules.rules['teams']:
                rows=self.ts.rankings(season,team); pd.DataFrame(rows).drop(columns=['eligibility'],errors='ignore').to_excel(x,sheet_name=team,index=False)
        return path
    def pdf_team(self,season,team):
        from reportlab.lib.pagesizes import landscape,letter
        from reportlab.platypus import SimpleDocTemplate,Table,TableStyle,Paragraph,Spacer
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        path=EXPORTS/f'{season}_{team}_standings.pdf'; rows=self.ts.rankings(season,team); styles=getSampleStyleSheet(); doc=SimpleDocTemplate(str(path),pagesize=landscape(letter))
        data=[['Rank','Selected','Shooter','ATA','HOA','S','H','D','Eligible']]
        for r in rows: data.append([r['rank'],'Yes' if r['selected'] else '',r['display_name'],r.get('ata_number') or '',f"{r['hoa']:.2f}",r['singles_targets'],r['handicap_targets'],r['doubles_targets'],'Yes' if r['eligible'] else 'No'])
        t=Table(data,repeatRows=1); t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.lightgrey),('GRID',(0,0),(-1,-1),.5,colors.grey),('FONTSIZE',(0,0),(-1,-1),8)]))
        doc.build([Paragraph(f'{season} Minnesota {team} State Team Standings',styles['Title']),Spacer(1,12),t]); return path

def open_shootata_login(): webbrowser.open('https://shootata.com/Shooter-Information-Center')
