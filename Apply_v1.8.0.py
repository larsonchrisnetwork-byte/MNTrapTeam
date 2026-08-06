from pathlib import Path

gui_path = Path("mntrapteam/gui.py")
text = gui_path.read_text(encoding="utf-8")

if "from .analytics import personal_progress" not in text:
    text = text.replace(
        "from .planner import projected_team_rank, required_uniform_average_for_cut",
        "from .planner import projected_team_rank, required_uniform_average_for_cut\n"
        "from .analytics import personal_progress",
    )

old_tabs = (
    "self.dashboard=self.make_dashboard(); self.shooters=self.make_shooters(); "
    "self.imports=self.make_imports(); self.standings=self.make_standings(); "
    "self.projections=self.make_projections(); self.archive=self.make_archive(); "
    "self.settings_tab=self.make_settings()"
)
new_tabs = (
    "self.dashboard=self.make_dashboard(); self.progress=self.make_progress(); "
    "self.shooters=self.make_shooters(); self.imports=self.make_imports(); "
    "self.standings=self.make_standings(); self.projections=self.make_projections(); "
    "self.archive=self.make_archive(); self.settings_tab=self.make_settings()"
)
if old_tabs in text:
    text = text.replace(old_tabs, new_tabs)
elif "self.progress=self.make_progress()" not in text:
    raise RuntimeError("Could not locate the main tab initialization in gui.py")

progress_method = '''    def make_progress(self):
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
'''

if "    def make_progress(self):" not in text:
    marker = "    def make_shooters(self):"
    if marker not in text:
        raise RuntimeError("Could not locate make_shooters in gui.py")
    text = text.replace(marker, progress_method + marker)

old_refresh = (
    "def refresh_all(self): self.refresh_dashboard(); self.refresh_shooters(); "
    "self.refresh_standings(); self.refresh_projection_shooters(); "
    "self.refresh_snapshots(); self.refresh_imports()"
)
new_refresh = (
    "def refresh_all(self): self.refresh_dashboard(); self.refresh_progress(); "
    "self.refresh_shooters(); self.refresh_standings(); "
    "self.refresh_projection_shooters(); self.refresh_snapshots(); "
    "self.refresh_imports()"
)
if old_refresh in text:
    text = text.replace(old_refresh, new_refresh)
elif "self.refresh_progress()" not in text:
    raise RuntimeError("Could not locate refresh_all in gui.py")

refresh_method = '''    def refresh_progress(self):
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
'''

if "    def refresh_progress(self):" not in text:
    marker = "    def refresh_dashboard(self):"
    if marker not in text:
        raise RuntimeError("Could not locate refresh_dashboard in gui.py")
    text = text.replace(marker, refresh_method + marker)

for old in ("MNTrapTeam 1.5", "MNTrapTeam 1.6", "MNTrapTeam 1.7"):
    text = text.replace(old, "MNTrapTeam 1.8")

gui_path.write_text(text, encoding="utf-8")
Path("VERSION").write_text("1.8.0\n", encoding="utf-8")
print("MNTrapTeam 1.8.0 My Progress dashboard applied.")
