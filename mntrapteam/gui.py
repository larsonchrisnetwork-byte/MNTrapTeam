from __future__ import annotations
import json
from pathlib import Path
from PySide6.QtCore import Qt,QAbstractTableModel,QModelIndex
from PySide6.QtGui import QAction
from PySide6.QtWidgets import *
from .paths import CONFIG
from .services import TeamService,ExportService,open_shootata_login
from .importers import ScoreboardImporter
from .ingestion import TrackedOfficialStatsImporter,BatchImportService
from .planner import projected_team_rank, required_uniform_average_for_cut
from .analytics import personal_progress
from .sample_data import load as load_sample
from .race import team_race
from .event_intelligence import event_intelligence
from .race_changes import race_changes_from_latest_snapshot

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
        self.setWindowTitle('MNTrapTeam 2.4.0'); self.resize(1320,820); self.setStyleSheet(DARK)
        self.tabs=QTabWidget(); self.setCentralWidget(self.tabs)
        self.dashboard=self.make_dashboard(); self.progress=self.make_progress(); self.race=self.make_race(); self.shooters=self.make_shooters(); self.imports=self.make_imports(); self.standings=self.make_standings(); self.projections=self.make_projections(); self.archive=self.make_archive(); self.event_intelligence=self.make_event_intelligence(); self.race_changes=self.make_race_changes(); self.settings_tab=self.make_settings()
        self.make_menu(); self.refresh_all()
    def make_menu(self):
        f=self.menuBar().addMenu('&File');
        for text,fn in [('Backup database',self.backup),('Export all teams to Excel',self.export_all),('Exit',self.close)]: a=QAction(text,self); a.triggered.connect(fn); f.addAction(a)
        h=self.menuBar().addMenu('&Help'); a=QAction('Open ShootATA login',self); a.triggered.connect(open_shootata_login); h.addAction(a)
    def make_dashboard(self):
        w=QWidget(); v=QVBoxLayout(w); top=QHBoxLayout(); self.season_box=QSpinBox(); self.season_box.setRange(2000,2100); self.season_box.setValue(self.season); self.season_box.valueChanged.connect(self.change_season); top.addWidget(QLabel('Target year')); top.addWidget(self.season_box); top.addStretch(); b=QPushButton('Load sample data'); b.clicked.connect(self.load_sample); top.addWidget(b); v.addLayout(top)
        self.cards=QLabel(); self.cards.setTextFormat(Qt.RichText); self.cards.setMinimumHeight(130); v.addWidget(self.cards)
        self.dash_table=QTableView(); v.addWidget(self.dash_table); self.tabs.addTab(w,'Dashboard'); return w
    def make_progress(self):
        w=QWidget(); v=QVBoxLayout(w)
        note=QLabel('Uses the ATA number saved under Settings. Event totals come from imported score records; official season totals remain authoritative.')
        note.setWordWrap(True); v.addWidget(note)
        row=QHBoxLayout()
        refresh=QPushButton('Refresh my progress'); refresh.clicked.connect(self.refresh_progress); row.addWidget(refresh)
        row.addStretch(); v.addLayout(row)
        self.progress_cards=QLabel(); self.progress_cards.setTextFormat(Qt.RichText); self.progress_cards.setWordWrap(True); v.addWidget(self.progress_cards)
        self.progress_disciplines=QTableView(); v.addWidget(QLabel('Discipline progress')); v.addWidget(self.progress_disciplines)
        self.progress_events=QTableView(); v.addWidget(QLabel('Recent imported events')); v.addWidget(self.progress_events)
        self.tabs.addTab(w,'My Progress'); return w
    def make_race(self):
        w=QWidget(); v=QVBoxLayout(w)
        controls=QHBoxLayout()
        self.race_team=QComboBox(); self.race_team.addItems(self.rules.rules['teams'])
        self.race_team.currentTextChanged.connect(self.refresh_race)
        controls.addWidget(QLabel('Team')); controls.addWidget(self.race_team)
        self.race_bubble=QDoubleSpinBox(); self.race_bubble.setRange(0,5); self.race_bubble.setDecimals(2); self.race_bubble.setSingleStep(.05); self.race_bubble.setValue(.75)
        self.race_bubble.valueChanged.connect(self.refresh_race)
        controls.addWidget(QLabel('Bubble width')); controls.addWidget(self.race_bubble)
        refresh=QPushButton('Refresh race'); refresh.clicked.connect(self.refresh_race); controls.addWidget(refresh)
        controls.addStretch(); v.addLayout(controls)
        self.race_cards=QLabel(); self.race_cards.setTextFormat(Qt.RichText); self.race_cards.setWordWrap(True); v.addWidget(self.race_cards)
        self.race_table=QTableView(); v.addWidget(self.race_table)
        self.tabs.addTab(w,'Team Race'); return w

    def make_progress(self):
        w=QWidget(); v=QVBoxLayout(w)
        note=QLabel(
            'Uses the ATA number saved under Settings. Imported event totals '
            'are shown separately from authoritative ShootATA season totals.'
        )
        note.setWordWrap(True); v.addWidget(note)
        controls=QHBoxLayout()
        refresh=QPushButton('Refresh my progress')
        refresh.clicked.connect(self.refresh_progress)
        controls.addWidget(refresh); controls.addStretch(); v.addLayout(controls)
        self.progress_cards=QLabel()
        self.progress_cards.setTextFormat(Qt.RichText)
        self.progress_cards.setWordWrap(True)
        v.addWidget(self.progress_cards)
        self.progress_disciplines=QTableView()
        v.addWidget(QLabel('Discipline progress'))
        v.addWidget(self.progress_disciplines)
        self.progress_events=QTableView()
        v.addWidget(QLabel('Recent imported events'))
        v.addWidget(self.progress_events)
        self.tabs.addTab(w,'My Progress')
        return w


    def make_race(self):
        w=QWidget(); v=QVBoxLayout(w)
        controls=QHBoxLayout()
        self.race_team=QComboBox()
        self.race_team.addItems(self.rules.rules['teams'])
        self.race_team.currentTextChanged.connect(self.refresh_race)
        controls.addWidget(QLabel('Team')); controls.addWidget(self.race_team)
        self.race_bubble=QDoubleSpinBox()
        self.race_bubble.setRange(0,5)
        self.race_bubble.setDecimals(2)
        self.race_bubble.setSingleStep(.05)
        self.race_bubble.setValue(.75)
        self.race_bubble.valueChanged.connect(self.refresh_race)
        controls.addWidget(QLabel('Bubble width'))
        controls.addWidget(self.race_bubble)
        refresh=QPushButton('Refresh race')
        refresh.clicked.connect(self.refresh_race)
        controls.addWidget(refresh); controls.addStretch(); v.addLayout(controls)
        self.race_cards=QLabel()
        self.race_cards.setTextFormat(Qt.RichText)
        self.race_cards.setWordWrap(True)
        v.addWidget(self.race_cards)
        self.race_table=QTableView()
        v.addWidget(self.race_table)
        self.tabs.addTab(w,'Team Race')
        return w


    def make_event_intelligence(self):
        w=QWidget(); v=QVBoxLayout(w)
        controls=QHBoxLayout()
        self.event_shooter=QComboBox()
        self.event_shooter.currentIndexChanged.connect(self.refresh_event_intelligence)
        controls.addWidget(QLabel('Shooter')); controls.addWidget(self.event_shooter)
        self.event_window=QSpinBox()
        self.event_window.setRange(100,5000)
        self.event_window.setSingleStep(100)
        self.event_window.setValue(500)
        self.event_window.valueChanged.connect(self.refresh_event_intelligence)
        controls.addWidget(QLabel('Recent-form targets')); controls.addWidget(self.event_window)
        refresh=QPushButton('Refresh')
        refresh.clicked.connect(self.refresh_event_intelligence)
        controls.addWidget(refresh); controls.addStretch(); v.addLayout(controls)

        self.event_cards=QLabel()
        self.event_cards.setTextFormat(Qt.RichText)
        self.event_cards.setWordWrap(True)
        v.addWidget(self.event_cards)

        self.event_subtabs=QTabWidget()
        self.event_recent=QTableView()
        self.event_bests=QTableView()
        self.event_clubs=QTableView()
        self.event_months=QTableView()
        self.event_history_table=QTableView()
        self.event_subtabs.addTab(self.event_recent,'Recent Form')
        self.event_subtabs.addTab(self.event_bests,'Personal Bests')
        self.event_subtabs.addTab(self.event_clubs,'By Club')
        self.event_subtabs.addTab(self.event_months,'By Month')
        self.event_subtabs.addTab(self.event_history_table,'Event History')
        v.addWidget(self.event_subtabs)
        self.tabs.addTab(w,'Event Intelligence')
        return w


    def make_race_changes(self):
        w=QWidget(); v=QVBoxLayout(w)
        controls=QHBoxLayout()
        self.changes_team=QComboBox()
        self.changes_team.addItems(self.rules.rules['teams'])
        self.changes_team.currentTextChanged.connect(self.refresh_race_changes)
        controls.addWidget(QLabel('Team')); controls.addWidget(self.changes_team)
        refresh=QPushButton('Compare with latest snapshot')
        refresh.clicked.connect(self.refresh_race_changes)
        controls.addWidget(refresh)
        snapshot=QPushButton('Save snapshot now')
        snapshot.clicked.connect(self.save_changes_snapshot)
        controls.addWidget(snapshot)
        controls.addStretch(); v.addLayout(controls)
        self.changes_cards=QLabel()
        self.changes_cards.setTextFormat(Qt.RichText)
        self.changes_cards.setWordWrap(True)
        v.addWidget(self.changes_cards)
        self.changes_table=QTableView()
        v.addWidget(self.changes_table)
        self.tabs.addTab(w,'Race Changes')
        return w

    def make_shooters(self):
        w=QWidget(); v=QVBoxLayout(w); form=QHBoxLayout(); self.q=QLineEdit(); self.q.setPlaceholderText('Search name or ATA number'); self.q.textChanged.connect(self.refresh_shooters); form.addWidget(self.q); add=QPushButton('Add / edit shooter'); add.clicked.connect(self.edit_shooter); form.addWidget(add); stats=QPushButton('Edit season stats'); stats.clicked.connect(self.edit_stats); form.addWidget(stats); v.addLayout(form); self.shooter_table=QTableView(); self.shooter_table.doubleClicked.connect(self.edit_shooter); v.addWidget(self.shooter_table); self.tabs.addTab(w,'Shooters'); return w
    def make_imports(self):
        w=QWidget(); v=QVBoxLayout(w); info=QLabel('Import official ShootATA exports or ShootScoreBoard CSV/XLSX/HTML/PDF reports. ShootScoreBoard data is treated as unofficial.'); info.setWordWrap(True); v.addWidget(info)
        row=QHBoxLayout(); b1=QPushButton('Import official ShootATA file'); b1.clicked.connect(self.import_official); row.addWidget(b1); b2=QPushButton('Import ShootScoreBoard report'); b2.clicked.connect(self.import_scoreboard); row.addWidget(b2); batch=QPushButton('Import folder'); batch.clicked.connect(self.import_folder); row.addWidget(batch); b3=QPushButton('Open ShootATA login'); b3.clicked.connect(open_shootata_login); row.addWidget(b3); row.addStretch(); v.addLayout(row)
        self.import_log=QTextEdit(); self.import_log.setReadOnly(True); v.addWidget(self.import_log); self.import_table=QTableView(); v.addWidget(QLabel('Import history')); v.addWidget(self.import_table); self.tabs.addTab(w,'Imports'); return w
    def make_standings(self):
        w=QWidget(); v=QVBoxLayout(w); row=QHBoxLayout(); self.team_box=QComboBox(); self.team_box.addItems(self.rules.rules['teams']); self.team_box.currentTextChanged.connect(self.refresh_standings); row.addWidget(QLabel('Team')); row.addWidget(self.team_box); row.addStretch();
        for txt,fn in [('CSV',self.export_csv),('Excel all teams',self.export_all),('PDF',self.export_pdf)]: b=QPushButton('Export '+txt); b.clicked.connect(fn); row.addWidget(b)
        v.addLayout(row); self.stand_table=QTableView(); v.addWidget(self.stand_table); self.tabs.addTab(w,'State Teams'); return w
    def make_projections(self):
        w=QWidget(); f=QFormLayout(w)
        self.proj_shooter=QComboBox(); f.addRow('Shooter',self.proj_shooter)
        self.proj_team=QComboBox(); self.proj_team.addItems(self.rules.rules['teams']); f.addRow('Team',self.proj_team)
        self.proj_inputs={}
        for disc in ('singles','handicap','doubles'):
            row=QHBoxLayout()
            targets=QSpinBox(); targets.setRange(0,10000); targets.setSingleStep(100)
            avg=QDoubleSpinBox(); avg.setRange(0,100); avg.setDecimals(2); avg.setValue(95)
            row.addWidget(QLabel('Targets')); row.addWidget(targets)
            row.addWidget(QLabel('Expected average')); row.addWidget(avg)
            self.proj_inputs[disc]=(targets,avg)
            f.addRow(disc.title(),row)
        buttons=QHBoxLayout()
        b=QPushButton('Calculate projected rank'); b.clicked.connect(self.calc_projection); buttons.addWidget(b)
        needed=QPushButton('Average needed to make team'); needed.clicked.connect(self.calc_needed_for_cut); buttons.addWidget(needed)
        f.addRow(buttons)
        self.proj_result=QLabel(); self.proj_result.setWordWrap(True)
        self.proj_result.setTextInteractionFlags(Qt.TextSelectableByMouse)
        f.addRow(self.proj_result)
        self.tabs.addTab(w,'Projections'); return w

    def make_archive(self):
        w=QWidget(); v=QVBoxLayout(w); row=QHBoxLayout(); self.snap_label=QLineEdit(); self.snap_label.setPlaceholderText('Snapshot label'); row.addWidget(self.snap_label); b=QPushButton('Create season snapshot'); b.clicked.connect(self.snapshot); row.addWidget(b); v.addLayout(row); self.snap_table=QTableView(); v.addWidget(self.snap_table); self.tabs.addTab(w,'Archives'); return w
    def make_settings(self):
        w=QWidget(); f=QFormLayout(w); self.user_ata=QLineEdit(self.settings.get('user_ata_number','')); f.addRow('Your ATA number',self.user_ata); self.threshold=QSpinBox(); self.threshold.setRange(50,100); self.threshold.setValue(int(self.settings.get('fuzzy_match_threshold',88))); f.addRow('Name-match threshold',self.threshold); b=QPushButton('Save settings'); b.clicked.connect(self.save_settings); f.addRow(b); self.tabs.addTab(w,'Settings'); return w
    def change_season(self,y): self.season=y; self.refresh_all()
    def refresh_all(self): self.refresh_dashboard(); self.refresh_progress(); self.refresh_race(); self.refresh_shooters(); self.refresh_standings(); self.refresh_projection_shooters(); self.refresh_snapshots(); self.refresh_imports(); self.refresh_event_shooters(); self.refresh_event_intelligence(); self.refresh_race_changes()
    def refresh_imports(self):
        if hasattr(self,'import_table'):
            rows=self.db.query('SELECT filename,kind,rows_read,rows_imported,imported_at,warnings FROM imports ORDER BY id DESC LIMIT 100')
            self.import_table.setModel(DictModel(rows,[('filename','File'),('kind','Type'),('rows_read','Rows'),('rows_imported','Imported'),('imported_at','Imported at'),('warnings','Warnings')]))
    def refresh_progress(self):
        if not hasattr(self,'progress_cards'): return
        ata=self.user_ata.text() if hasattr(self,'user_ata') else self.settings.get('user_ata_number','')
        result=personal_progress(self.db,self.ts,self.season,ata)
        if not result.get('found'):
            self.progress_cards.setText('<h2>My Progress</h2><p>'+result.get('message','Set your ATA number in Settings.')+'</p>')
            self.progress_disciplines.setModel(DictModel([],[])); self.progress_events.setModel(DictModel([],[])); return
        shooter=result['shooter']
        if not result.get('has_stats'):
            self.progress_cards.setText(f"<h2>{shooter['display_name']}</h2><p>{result.get('message','No season statistics.')}</p>")
        else:
            ranked=result.get('ranking') or {}
            gap=ranked.get('hoa_gap_to_cut')
            gap_text='Cut line not established' if gap is None else f"{gap:+.2f} HOA points from cut"
            reasons='<br>'.join(result.get('eligibility_reasons') or ['All eligibility requirements currently met'])
            self.progress_cards.setText(
                f"<h2>{shooter['display_name']} — {self.season}</h2>"
                f"<b>Team:</b> {result['team']} &nbsp;&nbsp; "
                f"<b>HOA:</b> {ranked.get('hoa',0):.2f}% &nbsp;&nbsp; "
                f"<b>Rank:</b> {ranked.get('rank','—')} &nbsp;&nbsp; "
                f"<b>Status:</b> {'On team' if ranked.get('selected') else 'Outside team'}<br>"
                f"<b>Cut comparison:</b> {gap_text}<br>"
                f"<b>Eligibility:</b> {'Eligible' if result['eligible'] else 'Not yet eligible'}<br>{reasons}"
            )
        discs=list(result.get('disciplines',{}).values())
        for row in discs:
            row['recent_500']=result.get('recent_500_average',{}).get(row['discipline'],0)
        self.progress_disciplines.setModel(DictModel(discs,[('discipline','Discipline'),('targets','Imported Targets'),('hits','Hits'),('average','Imported Avg'),('recent_500','Recent 500 Avg'),('mn_targets','MN Targets'),('events','Events'),('mn_clubs','MN Clubs')]))
        events=result.get('events',[])[:50]
        self.progress_events.setModel(DictModel(events,[('event_date','Date'),('event_name','Event'),('discipline','Discipline'),('hits','Hits'),('targets','Targets'),('average','Average'),('location','Location'),('mn','MN'),('source','Source')]))
    def refresh_race(self):
        if not hasattr(self,'race_team'): return
        team=self.race_team.currentText()
        rankings=self.ts.rankings(self.season,team)
        size=int(self.rules.rules['teams'][team]['size'])
        result=team_race(rankings,size,self.race_bubble.value(),5)
        summary=result['summary']; cut=summary['cut_line_hoa']
        cut_text='Not established' if cut is None else f"{cut:.2f}%"
        self.race_cards.setText(
            f"<h2>{self.season} {team} Team Race</h2>"
            f"<b>{summary['selected']}/{summary['team_size']}</b> positions filled &nbsp;&nbsp; "
            f"<b>{summary['eligible']}</b> eligible shooters &nbsp;&nbsp; "
            f"<b>{summary['tracked']}</b> tracked &nbsp;&nbsp; "
            f"<b>Cut:</b> {cut_text} &nbsp;&nbsp; "
            f"<b>Bubble:</b> within {result['bubble_width']:.2f} HOA"
        )
        self.race_table.setModel(DictModel(result['rows'],[
            ('rank','Rank'),('race_status','Race Status'),('selected','Team'),
            ('eligible','Eligible'),('display_name','Shooter'),('ata_number','ATA #'),
            ('hoa','HOA'),('cut_line_hoa','Cut HOA'),('hoa_gap_to_cut','Gap'),
            ('birds_per_300_gap','Birds / 300'),('singles_targets','Singles'),
            ('handicap_targets','Handicap'),('doubles_targets','Doubles'),
            ('mn_clubs','MN Clubs'),('eligibility_reasons','Missing Requirements')
        ]))

    def refresh_progress(self):
        if not hasattr(self,'progress_cards'):
            return
        ata=(
            self.user_ata.text()
            if hasattr(self,'user_ata')
            else self.settings.get('user_ata_number','')
        )
        result=personal_progress(self.db,self.ts,self.season,ata)
        if not result.get('found'):
            self.progress_cards.setText(
                '<h2>My Progress</h2><p>'
                + result.get('message','Set your ATA number in Settings.')
                + '</p>'
            )
            self.progress_disciplines.setModel(DictModel([],[]))
            self.progress_events.setModel(DictModel([],[]))
            return
        shooter=result['shooter']
        if not result.get('has_stats'):
            self.progress_cards.setText(
                f"<h2>{shooter['display_name']}</h2>"
                f"<p>{result.get('message','No season statistics.')}</p>"
            )
        else:
            ranked=result.get('ranking') or {}
            gap=ranked.get('hoa_gap_to_cut')
            gap_text=(
                'Cut line not established'
                if gap is None
                else f"{gap:+.2f} HOA points from cut"
            )
            reasons='<br>'.join(
                result.get('eligibility_reasons')
                or ['All eligibility requirements currently met']
            )
            self.progress_cards.setText(
                f"<h2>{shooter['display_name']} — {self.season}</h2>"
                f"<b>Team:</b> {result['team']} &nbsp;&nbsp; "
                f"<b>HOA:</b> {ranked.get('hoa',0):.2f}% &nbsp;&nbsp; "
                f"<b>Rank:</b> {ranked.get('rank','—')} &nbsp;&nbsp; "
                f"<b>Status:</b> "
                f"{'On team' if ranked.get('selected') else 'Outside team'}<br>"
                f"<b>Cut comparison:</b> {gap_text}<br>"
                f"<b>Eligibility:</b> "
                f"{'Eligible' if result['eligible'] else 'Not yet eligible'}"
                f"<br>{reasons}"
            )
        disciplines=list(result.get('disciplines',{}).values())
        recent=result.get('recent_500_average',{})
        for row in disciplines:
            row['recent_500']=recent.get(row['discipline'],0)
        self.progress_disciplines.setModel(
            DictModel(
                disciplines,
                [
                    ('discipline','Discipline'),
                    ('targets','Imported Targets'),
                    ('hits','Hits'),
                    ('average','Imported Avg'),
                    ('recent_500','Recent 500 Avg'),
                    ('mn_targets','MN Targets'),
                    ('events','Events'),
                    ('mn_clubs','MN Clubs'),
                ],
            )
        )
        self.progress_events.setModel(
            DictModel(
                result.get('events',[])[:50],
                [
                    ('event_date','Date'),
                    ('event_name','Event'),
                    ('discipline','Discipline'),
                    ('hits','Hits'),
                    ('targets','Targets'),
                    ('average','Average'),
                    ('location','Location'),
                    ('mn','MN'),
                    ('source','Source'),
                ],
            )
        )


    def refresh_race(self):
        if not hasattr(self,'race_team'):
            return
        team=self.race_team.currentText()
        rankings=self.ts.rankings(self.season,team)
        size=int(self.rules.rules['teams'][team]['size'])
        result=team_race(
            rankings,
            size,
            self.race_bubble.value(),
            include_outside=5,
        )
        summary=result['summary']
        cut=summary['cut_line_hoa']
        cut_text='Not established' if cut is None else f"{cut:.2f}%"
        self.race_cards.setText(
            f"<h2>{self.season} {team} Team Race</h2>"
            f"<b>{summary['selected']}/{summary['team_size']}</b> "
            f"positions filled &nbsp;&nbsp; "
            f"<b>{summary['eligible']}</b> eligible &nbsp;&nbsp; "
            f"<b>{summary['tracked']}</b> tracked &nbsp;&nbsp; "
            f"<b>Cut:</b> {cut_text} &nbsp;&nbsp; "
            f"<b>Bubble:</b> within {result['bubble_width']:.2f} HOA"
        )
        self.race_table.setModel(
            DictModel(
                result['rows'],
                [
                    ('rank','Rank'),
                    ('race_status','Race Status'),
                    ('selected','Team'),
                    ('eligible','Eligible'),
                    ('display_name','Shooter'),
                    ('ata_number','ATA #'),
                    ('hoa','HOA'),
                    ('cut_line_hoa','Cut HOA'),
                    ('hoa_gap_to_cut','Gap'),
                    ('birds_per_300_gap','Birds / 300'),
                    ('singles_targets','Singles'),
                    ('handicap_targets','Handicap'),
                    ('doubles_targets','Doubles'),
                    ('mn_clubs','MN Clubs'),
                    ('eligibility_reasons','Missing Requirements'),
                ],
            )
        )


    def refresh_event_shooters(self):
        if not hasattr(self,'event_shooter'):
            return
        current=self.event_shooter.currentData()
        current_id=current.get('id') if isinstance(current,dict) else None
        self.event_shooter.blockSignals(True)
        self.event_shooter.clear()
        rows=self.db.query(
            'SELECT id,ata_number,display_name FROM shooters '
            'WHERE active=1 ORDER BY last_name,first_name,display_name'
        )
        selected_index=0
        for index,row in enumerate(rows):
            self.event_shooter.addItem(row['display_name'],row)
            if current_id and row['id']==current_id:
                selected_index=index
        if rows:
            self.event_shooter.setCurrentIndex(selected_index)
        self.event_shooter.blockSignals(False)

    def refresh_event_intelligence(self):
        if not hasattr(self,'event_shooter'):
            return
        shooter=self.event_shooter.currentData()
        if not shooter:
            self.event_cards.setText(
                '<h2>Event Intelligence</h2><p>No shooter selected.</p>'
            )
            return
        result=event_intelligence(
            self.db,
            shooter['id'],
            self.season,
            self.event_window.value(),
        )
        summary=result['summary']
        self.event_cards.setText(
            f"<h2>{shooter['display_name']} — {self.season}</h2>"
            f"<b>{summary['event_rows']}</b> imported event rows &nbsp;&nbsp; "
            f"<b>{summary['total_targets']:,}</b> targets &nbsp;&nbsp; "
            f"<b>{summary['clubs']}</b> clubs &nbsp;&nbsp; "
            f"<b>{summary['mn_clubs']}</b> MN clubs &nbsp;&nbsp; "
            f"<b>{summary['total_straights']}</b> perfect event scores"
        )
        self.event_recent.setModel(
            DictModel(
                result['recent_form'],
                [('discipline','Discipline'),('hits','Hits'),
                 ('targets','Targets'),('average','Average'),
                 ('events','Events Used'),('requested_window','Requested Window')],
            )
        )
        self.event_bests.setModel(
            DictModel(
                result['personal_bests'],
                [('discipline','Discipline'),('hits','Hits'),
                 ('targets','Targets'),('average','Average'),
                 ('event_date','Date'),('event_name','Event'),('club','Club')],
            )
        )
        self.event_clubs.setModel(
            DictModel(
                result['clubs'],
                [('club_display','Club'),('discipline','Discipline'),
                 ('hits','Hits'),('targets','Targets'),('average','Average'),
                 ('events','Events'),('straights','Perfect Scores')],
            )
        )
        self.event_months.setModel(
            DictModel(
                result['months'],
                [('month','Month'),('discipline','Discipline'),
                 ('hits','Hits'),('targets','Targets'),('average','Average'),
                 ('events','Events'),('straights','Perfect Scores')],
            )
        )
        self.event_history_table.setModel(
            DictModel(
                result['events'],
                [('event_date','Date'),('event_name','Event'),
                 ('club_display','Club'),('discipline','Discipline'),
                 ('hits','Hits'),('targets','Targets'),('average','Average'),
                 ('straight','Perfect'),('in_state','MN'),('source','Source')],
            )
        )


    def refresh_race_changes(self):
        if not hasattr(self,'changes_team'):
            return
        team=self.changes_team.currentText()
        result=race_changes_from_latest_snapshot(
            self.db,
            self.ts,
            self.season,
            team,
        )
        if not result.get('has_snapshot'):
            self.changes_cards.setText(
                f"<h2>{self.season} {team} Race Changes</h2>"
                f"<p>{result.get('message','No snapshot available.')}</p>"
            )
            self.changes_table.setModel(DictModel([],[]))
            return

        old_cut=result.get('old_cut_line')
        new_cut=result.get('new_cut_line')
        cut_change=result.get('cut_line_change')
        cut_text=(
            'Not established'
            if old_cut is None or new_cut is None
            else f"{old_cut:.2f}% → {new_cut:.2f}% ({cut_change:+.2f})"
        )
        self.changes_cards.setText(
            f"<h2>{self.season} {team} Race Changes</h2>"
            f"<b>Compared with:</b> {result.get('snapshot_label') or 'Snapshot'} "
            f"({result.get('snapshot_created_at') or 'unknown time'})<br>"
            f"<b>Cut-line change:</b> {cut_text}<br>"
            f"<b>{len(result.get('changes',[]))}</b> shooter changes detected"
        )
        self.changes_table.setModel(
            DictModel(
                result.get('changes',[]),
                [
                    ('team_change','Team Change'),
                    ('display_name','Shooter'),
                    ('old_rank','Old Rank'),
                    ('new_rank','New Rank'),
                    ('rank_change','Positions'),
                    ('old_hoa','Old HOA'),
                    ('new_hoa','New HOA'),
                    ('hoa_change','HOA Change'),
                    ('change_type','Change Type'),
                ],
            )
        )

    def save_changes_snapshot(self):
        team=self.changes_team.currentText()
        label,ok=QInputDialog.getText(
            self,
            'Snapshot label',
            'Label for this standings snapshot',
        )
        if not ok:
            return
        self.ts.snapshot(self.season,label or f"{team} snapshot")
        self.refresh_snapshots()
        self.refresh_race_changes()

    def refresh_dashboard(self):
        rows=self.ts.season_rows(self.season); elig=sum(1 for r in rows if r['eligibility'].eligible); self.cards.setText(f'<h2>{self.season} Minnesota State Team Dashboard</h2><b>{len(rows)}</b> tracked shooters &nbsp;&nbsp; <b>{elig}</b> currently eligible &nbsp;&nbsp; <b>{len(self.db.query("SELECT id FROM imports"))}</b> imported files')
        top=sorted(rows,key=lambda r:r['hoa'],reverse=True)[:20]; self.dash_table.setModel(DictModel(top,[('display_name','Shooter'),('category','Category'),('hoa','HOA'),('cut_line_hoa','Cut HOA'),('hoa_gap_to_cut','Gap to Cut'),('birds_per_300_gap','Birds / 300'),('singles_targets','Singles'),('handicap_targets','Handicap'),('doubles_targets','Doubles')]))
    def refresh_shooters(self):
        q='%' + (self.q.text() if hasattr(self,'q') else '') + '%'; rows=self.db.query('SELECT * FROM shooters WHERE display_name LIKE ? OR ata_number LIKE ? ORDER BY last_name,first_name',(q,q)); self.shooter_rows=rows; self.shooter_table.setModel(DictModel(rows,[('ata_number','ATA #'),('display_name','Name'),('category','Category'),('state','State'),('yardage','Yardage')]))
    def refresh_standings(self):
        if not hasattr(self,'team_box'): return
        rows=self.ts.rankings(self.season,self.team_box.currentText()); self.stand_table.setModel(DictModel(rows,[('rank','Rank'),('selected','Team'),('eligible','Eligible'),('display_name','Shooter'),('ata_number','ATA #'),('hoa','HOA'),('cut_line_hoa','Cut HOA'),('hoa_gap_to_cut','Gap to Cut'),('birds_per_300_gap','Birds / 300'),('singles_targets','Singles'),('handicap_targets','Handicap'),('doubles_targets','Doubles'),('mn_clubs','MN Clubs'),('eligibility_reasons','Missing requirements')]))
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
    def edit_stats(self):
        idx=self.shooter_table.currentIndex()
        if not idx.isValid() or idx.row()>=len(self.shooter_rows):
            QMessageBox.information(self,'Season stats','Select a shooter first.'); return
        shooter=self.shooter_rows[idx.row()]; sid=shooter['id']
        found=self.db.query('SELECT * FROM season_stats WHERE shooter_id=? AND season=?',(sid,self.season))
        row=found[0] if found else {}
        d=QDialog(self); d.setWindowTitle(f"{shooter['display_name']} — {self.season} statistics"); f=QFormLayout(d); fields={}
        for disc in ('singles','handicap','doubles'):
            box=QSpinBox(); box.setRange(0,200000); box.setValue(int(row.get(f'{disc}_targets') or 0)); fields[f'{disc}_targets']=box; f.addRow(f'{disc.title()} targets',box)
            hits=QSpinBox(); hits.setRange(0,200000); hits.setValue(int(row.get(f'{disc}_hits') or 0)); fields[f'{disc}_hits']=hits; f.addRow(f'{disc.title()} hits',hits)
            mn=QSpinBox(); mn.setRange(0,200000); mn.setValue(int(row.get(f'mn_{disc}_targets') or 0)); fields[f'mn_{disc}_targets']=mn; f.addRow(f'MN {disc} targets',mn)
        clubs=QSpinBox(); clubs.setRange(0,100); clubs.setValue(int(row.get('mn_clubs') or 0)); fields['mn_clubs']=clubs; f.addRow('Minnesota clubs',clubs)
        haa=QCheckBox(); haa.setChecked(bool(row.get('haa_complete'))); fields['haa_complete']=haa; f.addRow('HAA completed',haa)
        official=QCheckBox(); official.setChecked(bool(row.get('official'))); fields['official']=official; f.addRow('Official totals',official)
        bb=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel); bb.accepted.connect(d.accept); bb.rejected.connect(d.reject); f.addRow(bb)
        if d.exec():
            vals={k:(int(v.isChecked()) if isinstance(v,QCheckBox) else v.value()) for k,v in fields.items()}
            for disc in ('singles','handicap','doubles'):
                if vals[f'{disc}_hits']>vals[f'{disc}_targets']:
                    QMessageBox.warning(self,'Invalid statistics',f'{disc.title()} hits cannot exceed targets.'); return
            vals['source']='Manual entry'; self.db.upsert_stats(sid,self.season,**vals); self.refresh_all()
    def import_official(self):
        p,_=QFileDialog.getOpenFileName(self,'Official ShootATA export','','Data files (*.csv *.xlsx *.xlsm *.html *.htm *.pdf)')
        if p:
            try: n,w=TrackedOfficialStatsImporter(self.db).import_file(p,self.season); self.import_log.append(f'Official import: {n} shooters from {p}\n'+'\n'.join(w)); self.refresh_all()
            except Exception as e: QMessageBox.critical(self,'Import failed',str(e))
    def import_scoreboard(self):
        p,_=QFileDialog.getOpenFileName(self,'ShootScoreBoard report','','Reports (*.csv *.xlsx *.xlsm *.html *.htm *.pdf)')
        if not p:return
        club,ok=QInputDialog.getText(self,'Club','Minnesota club/location');
        if not ok:return
        try: n,w=ScoreboardImporter(self.db,self.threshold.value()).import_file(p,self.season,club=club,in_state=True); self.import_log.append(f'Scoreboard import: {n} event scores from {p}\n'+'\n'.join(w)); self.refresh_all()
        except Exception as e: QMessageBox.critical(self,'Import failed',str(e))
    def _projection_additions(self):
        return {disc:(boxes[0].value(),boxes[1].value()) for disc,boxes in self.proj_inputs.items()}
    def import_folder(self):
        folder=QFileDialog.getExistingDirectory(self,'Folder containing import files')
        if not folder:return
        club,ok=QInputDialog.getText(self,'Club','Default Minnesota club/location for score reports')
        if not ok:return
        results=BatchImportService(self.db,self.threshold.value()).import_folder(folder,self.season,club=club,in_state=True)
        lines=[]
        for result in results:
            status='ERROR' if result.error else ('DUPLICATE' if result.skipped_duplicate else 'IMPORTED')
            lines.append(f"{status}: {result.path.name} [{result.kind}] {result.rows_imported}/{result.rows_read}")
            if result.error: lines.append(f"  {result.error}")
            lines.extend(f"  {warning}" for warning in result.warnings)
        self.import_log.append('Folder import:\n'+'\n'.join(lines))
        self.refresh_all()
    def calc_projection(self):
        r=self.proj_shooter.currentData()
        if not r:return
        team=self.proj_team.currentText()
        try:
            result=projected_team_rank(self.ts.season_rows(self.season),r['id'],self._projection_additions(),self.rules,team)
        except ValueError as exc:
            QMessageBox.warning(self,'Projection',str(exc)); return
        shooter=result['shooter']; cut=result.get('cut_line_hoa'); gap=result.get('hoa_gap_to_cut')
        details=shooter['projection_details']
        lines=[f"<b>{shooter['display_name']}</b> projected HOA: <b>{shooter['hoa']:.2f}%</b>",
               f"Projected overall rank: <b>{result['rank']}</b>",
               f"Projected eligible rank: <b>{result.get('eligible_rank') or 'Not eligible'}</b>",
               f"Projected team status: <b>{'Selected' if result['selected'] else 'Outside team'}</b>"]
        if cut is not None: lines.append(f"Cut line: <b>{cut:.2f}%</b>; gap: <b>{gap:+.2f}</b>")
        for disc in ('singles','handicap','doubles'):
            d=details[disc]
            lines.append(f"{disc.title()}: {d['average']:.2f}% on {d['targets']:,} targets")
        self.proj_result.setText('<br>'.join(lines))
    def calc_needed_for_cut(self):
        r=self.proj_shooter.currentData()
        if not r:return
        future={disc:boxes[0].value() for disc,boxes in self.proj_inputs.items()}
        if not any(future.values()):
            QMessageBox.information(self,'Projection','Enter future targets in at least one discipline.'); return
        try:
            needed=required_uniform_average_for_cut(self.ts.season_rows(self.season),r['id'],future,self.rules,self.proj_team.currentText())
        except ValueError as exc:
            QMessageBox.warning(self,'Projection',str(exc)); return
        if needed is None:
            self.proj_result.setText('<b>Even 100% on the entered future targets would not place this shooter on the selected team.</b>')
        elif needed==0:
            self.proj_result.setText('<b>This shooter is already projected on the selected team.</b>')
        else:
            self.proj_result.setText(f"Approximate average needed across the entered future targets to make the team: <b>{needed:.2f}%</b>")

    def snapshot(self): self.ts.snapshot(self.season,self.snap_label.text() or 'Snapshot'); self.refresh_snapshots()
    def backup(self): QMessageBox.information(self,'Backup',f'Created {self.db.backup()}')
    def export_csv(self): QMessageBox.information(self,'Export',f'Created {self.ex.csv_team(self.season,self.team_box.currentText())}')
    def export_all(self): QMessageBox.information(self,'Export',f'Created {self.ex.xlsx_all(self.season)}')
    def export_pdf(self): QMessageBox.information(self,'Export',f'Created {self.ex.pdf_team(self.season,self.team_box.currentText())}')
    def save_settings(self):
        self.settings['season']=self.season; self.settings['user_ata_number']=self.user_ata.text(); self.settings['fuzzy_match_threshold']=self.threshold.value(); (CONFIG/'settings.json').write_text(json.dumps(self.settings,indent=2)); QMessageBox.information(self,'Settings','Settings saved.')
