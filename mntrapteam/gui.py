from __future__ import annotations
import json
from pathlib import Path
from PySide6.QtCore import Qt,QAbstractTableModel,QModelIndex
from PySide6.QtGui import QAction
from PySide6.QtWidgets import *
from .paths import CONFIG
from .services import TeamService,ExportService,open_shootata_login
from .importers import OfficialStatsImporter,ScoreboardImporter
from .calculations import project
from .sample_data import load as load_sample

DARK='''QWidget{background:#19212b;color:#e8edf2;font-size:10pt} QLineEdit,QComboBox,QSpinBox,QDoubleSpinBox,QTableView,QTextEdit{background:#111820;border:1px solid #3b4a5b;padding:5px} QPushButton{background:#2574a9;border:0;padding:7px 12px;border-radius:3px} QPushButton:hover{background:#328bc3} QHeaderView::section{background:#273545;padding:6px;border:0} QTabBar::tab{padding:9px 15px;background:#273545} QTabBar::tab:selected{background:#2574a9}'''

class DictModel(QAbstractTableModel):
    def __init__(self,rows=None,columns=None): super().__init__(); self.rows=rows or []; self.columns=columns or []
    def rowCount(self,parent=QModelIndex()): return len(self.rows)
    def columnCount(self,parent=QModelIndex()): return len(self.columns)
    def data(self,index,role=Qt.DisplayRole):
        if not index.isValid() or role not in (Qt.DisplayRole,Qt.EditRole): return None
        key,label=self.columns[index.column()]; v=self.rows[index.row()].get(key,'')
        if isinstance(v,float): return f'{v:.2f}'
        if isinstance(v,bool): return 'Yes' if v else 'No'
        return str(v if v is not None else '')
    def headerData(self,section,orientation,role=Qt.DisplayRole):
        if role==Qt.DisplayRole: return self.columns[section][1] if orientation==Qt.Horizontal else section+1

class MainWindow(QMainWindow):
    def __init__(self,db,rules,settings):
        super().__init__(); self.db=db; self.rules=rules; self.settings=settings; self.season=int(settings.get('season',2026)); self.ts=TeamService(db,rules); self.ex=ExportService(self.ts)
        self.setWindowTitle('MNTrapTeam 1.0'); self.resize(1320,820); self.setStyleSheet(DARK)
        self.tabs=QTabWidget(); self.setCentralWidget(self.tabs)
        self.dashboard=self.make_dashboard(); self.shooters=self.make_shooters(); self.imports=self.make_imports(); self.standings=self.make_standings(); self.projections=self.make_projections(); self.archive=self.make_archive(); self.settings_tab=self.make_settings()
        self.make_menu(); self.refresh_all()
    def make_menu(self):
        f=self.menuBar().addMenu('&File');
        for text,fn in [('Backup database',self.backup),('Export all teams to Excel',self.export_all),('Exit',self.close)]: a=QAction(text,self); a.triggered.connect(fn); f.addAction(a)
        h=self.menuBar().addMenu('&Help'); a=QAction('Open ShootATA login',self); a.triggered.connect(open_shootata_login); h.addAction(a)
    def make_dashboard(self):
        w=QWidget(); v=QVBoxLayout(w); top=QHBoxLayout(); self.season_box=QSpinBox(); self.season_box.setRange(2000,2100); self.season_box.setValue(self.season); self.season_box.valueChanged.connect(self.change_season); top.addWidget(QLabel('Target year')); top.addWidget(self.season_box); top.addStretch(); b=QPushButton('Load sample data'); b.clicked.connect(self.load_sample); top.addWidget(b); v.addLayout(top)
        self.cards=QLabel(); self.cards.setTextFormat(Qt.RichText); self.cards.setMinimumHeight(130); v.addWidget(self.cards)
        self.dash_table=QTableView(); v.addWidget(self.dash_table); self.tabs.addTab(w,'Dashboard'); return w
    def make_shooters(self):
        w=QWidget(); v=QVBoxLayout(w); form=QHBoxLayout(); self.q=QLineEdit(); self.q.setPlaceholderText('Search name or ATA number'); self.q.textChanged.connect(self.refresh_shooters); form.addWidget(self.q); add=QPushButton('Add / edit shooter'); add.clicked.connect(self.edit_shooter); form.addWidget(add); v.addLayout(form); self.shooter_table=QTableView(); self.shooter_table.doubleClicked.connect(self.edit_shooter); v.addWidget(self.shooter_table); self.tabs.addTab(w,'Shooters'); return w
    def make_imports(self):
        w=QWidget(); v=QVBoxLayout(w); info=QLabel('Import official ShootATA exports or ShootScoreBoard CSV/XLSX/HTML/PDF reports. ShootScoreBoard data is treated as unofficial.'); info.setWordWrap(True); v.addWidget(info)
        row=QHBoxLayout(); b1=QPushButton('Import official ShootATA file'); b1.clicked.connect(self.import_official); row.addWidget(b1); b2=QPushButton('Import ShootScoreBoard report'); b2.clicked.connect(self.import_scoreboard); row.addWidget(b2); b3=QPushButton('Open ShootATA login'); b3.clicked.connect(open_shootata_login); row.addWidget(b3); row.addStretch(); v.addLayout(row)
        self.import_log=QTextEdit(); self.import_log.setReadOnly(True); v.addWidget(self.import_log); self.tabs.addTab(w,'Imports'); return w
    def make_standings(self):
        w=QWidget(); v=QVBoxLayout(w); row=QHBoxLayout(); self.team_box=QComboBox(); self.team_box.addItems(self.rules.rules['teams']); self.team_box.currentTextChanged.connect(self.refresh_standings); row.addWidget(QLabel('Team')); row.addWidget(self.team_box); row.addStretch();
        for txt,fn in [('CSV',self.export_csv),('Excel all teams',self.export_all),('PDF',self.export_pdf)]: b=QPushButton('Export '+txt); b.clicked.connect(fn); row.addWidget(b)
        v.addLayout(row); self.stand_table=QTableView(); v.addWidget(self.stand_table); self.tabs.addTab(w,'State Teams'); return w
    def make_projections(self):
        w=QWidget(); f=QFormLayout(w); self.proj_shooter=QComboBox(); f.addRow('Shooter',self.proj_shooter); self.proj_disc=QComboBox(); self.proj_disc.addItems(['singles','handicap','doubles']); f.addRow('Discipline',self.proj_disc); self.proj_targets=QSpinBox(); self.proj_targets.setRange(0,10000); self.proj_targets.setValue(1000); f.addRow('Additional targets',self.proj_targets); self.proj_avg=QDoubleSpinBox(); self.proj_avg.setRange(0,100); self.proj_avg.setDecimals(2); self.proj_avg.setValue(95); f.addRow('Expected average',self.proj_avg); b=QPushButton('Calculate projection'); b.clicked.connect(self.calc_projection); f.addRow(b); self.proj_result=QLabel(); self.proj_result.setWordWrap(True); f.addRow(self.proj_result); self.tabs.addTab(w,'Projections'); return w
    def make_archive(self):
        w=QWidget(); v=QVBoxLayout(w); row=QHBoxLayout(); self.snap_label=QLineEdit(); self.snap_label.setPlaceholderText('Snapshot label'); row.addWidget(self.snap_label); b=QPushButton('Create season snapshot'); b.clicked.connect(self.snapshot); row.addWidget(b); v.addLayout(row); self.snap_table=QTableView(); v.addWidget(self.snap_table); self.tabs.addTab(w,'Archives'); return w
    def make_settings(self):
        w=QWidget(); f=QFormLayout(w); self.user_ata=QLineEdit(self.settings.get('user_ata_number','')); f.addRow('Your ATA number',self.user_ata); self.threshold=QSpinBox(); self.threshold.setRange(50,100); self.threshold.setValue(int(self.settings.get('fuzzy_match_threshold',88))); f.addRow('Name-match threshold',self.threshold); b=QPushButton('Save settings'); b.clicked.connect(self.save_settings); f.addRow(b); self.tabs.addTab(w,'Settings'); return w
    def change_season(self,y): self.season=y; self.refresh_all()
    def refresh_all(self): self.refresh_dashboard(); self.refresh_shooters(); self.refresh_standings(); self.refresh_projection_shooters(); self.refresh_snapshots()
    def refresh_dashboard(self):
        rows=self.ts.season_rows(self.season); elig=sum(1 for r in rows if r['eligibility'].eligible); self.cards.setText(f'<h2>{self.season} Minnesota State Team Dashboard</h2><b>{len(rows)}</b> tracked shooters &nbsp;&nbsp; <b>{elig}</b> currently eligible &nbsp;&nbsp; <b>{len(self.db.query("SELECT id FROM imports"))}</b> imported files')
        top=sorted(rows,key=lambda r:r['hoa'],reverse=True)[:20]; self.dash_table.setModel(DictModel(top,[('display_name','Shooter'),('category','Category'),('hoa','HOA'),('singles_targets','Singles'),('handicap_targets','Handicap'),('doubles_targets','Doubles')]))
    def refresh_shooters(self):
        q='%' + (self.q.text() if hasattr(self,'q') else '') + '%'; rows=self.db.query('SELECT * FROM shooters WHERE display_name LIKE ? OR ata_number LIKE ? ORDER BY last_name,first_name',(q,q)); self.shooter_rows=rows; self.shooter_table.setModel(DictModel(rows,[('ata_number','ATA #'),('display_name','Name'),('category','Category'),('state','State'),('yardage','Yardage')]))
    def refresh_standings(self):
        if not hasattr(self,'team_box'): return
        rows=self.ts.rankings(self.season,self.team_box.currentText()); self.stand_table.setModel(DictModel(rows,[('rank','Rank'),('selected','Team'),('eligible','Eligible'),('display_name','Shooter'),('ata_number','ATA #'),('hoa','HOA'),('singles_targets','Singles'),('handicap_targets','Handicap'),('doubles_targets','Doubles'),('mn_clubs','MN Clubs'),('eligibility_reasons','Missing requirements')]))
    def refresh_projection_shooters(self):
        if not hasattr(self,'proj_shooter'): return
        old=self.proj_shooter.currentData(); self.proj_shooter.clear()
        for r in self.ts.season_rows(self.season): self.proj_shooter.addItem(r['display_name'],r)
    def refresh_snapshots(self):
        if hasattr(self,'snap_table'): self.snap_table.setModel(DictModel(self.db.query('SELECT id,season,label,created_at FROM snapshots ORDER BY id DESC'),[('season','Season'),('label','Label'),('created_at','Created')]))
    def load_sample(self): load_sample(self.db,self.season); self.refresh_all(); QMessageBox.information(self,'Sample data','Sample shooters loaded.')
    def edit_shooter(self):
        row=None; idx=self.shooter_table.currentIndex();
        if idx.isValid() and idx.row()<len(self.shooter_rows): row=self.shooter_rows[idx.row()]
        d=QDialog(self); d.setWindowTitle('Shooter'); f=QFormLayout(d); ata=QLineEdit(row.get('ata_number','') if row else ''); name=QLineEdit(row.get('display_name','') if row else ''); cat=QComboBox(); cat.addItems(list(self.rules.rules['teams'])+['SUB_VET']); cat.setCurrentText(row.get('category','MEN') if row else 'MEN'); state=QLineEdit(row.get('state','MN') if row else 'MN'); f.addRow('ATA #',ata); f.addRow('Name',name); f.addRow('Category',cat); f.addRow('State',state); bb=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel); bb.accepted.connect(d.accept); bb.rejected.connect(d.reject); f.addRow(bb)
        if d.exec() and name.text().strip(): self.db.upsert_shooter(ata.text(),name.text(),cat.currentText(),state.text()); self.refresh_all()
    def import_official(self):
        p,_=QFileDialog.getOpenFileName(self,'Official ShootATA export','','Data files (*.csv *.xlsx *.xlsm *.html *.htm *.pdf)')
        if p:
            try: n,w=OfficialStatsImporter(self.db).import_file(p,self.season); self.import_log.append(f'Official import: {n} shooters from {p}\n'+'\n'.join(w)); self.refresh_all()
            except Exception as e: QMessageBox.critical(self,'Import failed',str(e))
    def import_scoreboard(self):
        p,_=QFileDialog.getOpenFileName(self,'ShootScoreBoard report','','Reports (*.csv *.xlsx *.xlsm *.html *.htm *.pdf)')
        if not p:return
        club,ok=QInputDialog.getText(self,'Club','Minnesota club/location');
        if not ok:return
        try: n,w=ScoreboardImporter(self.db,self.threshold.value()).import_file(p,self.season,club=club,in_state=True); self.import_log.append(f'Scoreboard import: {n} event scores from {p}\n'+'\n'.join(w)); self.refresh_all()
        except Exception as e: QMessageBox.critical(self,'Import failed',str(e))
    def calc_projection(self):
        r=self.proj_shooter.currentData();
        if not r:return
        d=self.proj_disc.currentText(); p=project(r[f'{d}_hits'],r[f'{d}_targets'],self.proj_targets.value(),self.proj_avg.value()); avgs={x:(r[f'{x}_hits']/r[f'{x}_targets']*100 if r[f'{x}_targets'] else 0) for x in ('singles','handicap','doubles')}; avgs[d]=p['average']; newhoa=sum(avgs.values())/3
        self.proj_result.setText(f"Projected {d.title()}: {p['average']:.2f}% on {p['targets']:,} targets. Projected HOA: {newhoa:.2f}%.")
    def snapshot(self): self.ts.snapshot(self.season,self.snap_label.text() or 'Snapshot'); self.refresh_snapshots()
    def backup(self): QMessageBox.information(self,'Backup',f'Created {self.db.backup()}')
    def export_csv(self): QMessageBox.information(self,'Export',f'Created {self.ex.csv_team(self.season,self.team_box.currentText())}')
    def export_all(self): QMessageBox.information(self,'Export',f'Created {self.ex.xlsx_all(self.season)}')
    def export_pdf(self): QMessageBox.information(self,'Export',f'Created {self.ex.pdf_team(self.season,self.team_box.currentText())}')
    def save_settings(self):
        self.settings['season']=self.season; self.settings['user_ata_number']=self.user_ata.text(); self.settings['fuzzy_match_threshold']=self.threshold.value(); (CONFIG/'settings.json').write_text(json.dumps(self.settings,indent=2)); QMessageBox.information(self,'Settings','Settings saved.')
