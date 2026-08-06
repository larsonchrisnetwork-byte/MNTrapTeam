from pathlib import Path

gui_path = Path("mntrapteam/gui.py")
text = gui_path.read_text(encoding="utf-8")

if "from .race import team_race" not in text:
    anchor = "from .sample_data import load as load_sample"
    if anchor not in text:
        raise RuntimeError("Could not locate GUI import anchor")
    text = text.replace(anchor, anchor + "\nfrom .race import team_race")

old_tabs = (
    "self.dashboard=self.make_dashboard(); self.shooters=self.make_shooters(); "
    "self.imports=self.make_imports(); self.standings=self.make_standings(); "
    "self.projections=self.make_projections(); self.archive=self.make_archive(); "
    "self.settings_tab=self.make_settings()"
)
new_tabs = (
    "self.dashboard=self.make_dashboard(); self.race=self.make_race(); "
    "self.shooters=self.make_shooters(); self.imports=self.make_imports(); "
    "self.standings=self.make_standings(); self.projections=self.make_projections(); "
    "self.archive=self.make_archive(); self.settings_tab=self.make_settings()"
)

old_tabs_progress = (
    "self.dashboard=self.make_dashboard(); self.progress=self.make_progress(); "
    "self.shooters=self.make_shooters(); self.imports=self.make_imports(); "
    "self.standings=self.make_standings(); self.projections=self.make_projections(); "
    "self.archive=self.make_archive(); self.settings_tab=self.make_settings()"
)
new_tabs_progress = (
    "self.dashboard=self.make_dashboard(); self.progress=self.make_progress(); "
    "self.race=self.make_race(); self.shooters=self.make_shooters(); "
    "self.imports=self.make_imports(); self.standings=self.make_standings(); "
    "self.projections=self.make_projections(); self.archive=self.make_archive(); "
    "self.settings_tab=self.make_settings()"
)

if old_tabs_progress in text:
    text = text.replace(old_tabs_progress, new_tabs_progress)
elif old_tabs in text:
    text = text.replace(old_tabs, new_tabs)
elif "self.race=self.make_race()" not in text:
    raise RuntimeError("Could not locate tab initialization")

race_method = '''    def make_race(self):
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
'''

if "    def make_race(self):" not in text:
    marker = "    def make_shooters(self):"
    if marker not in text:
        raise RuntimeError("Could not locate make_shooters")
    text = text.replace(marker, race_method + marker)

old_refresh = (
    "def refresh_all(self): self.refresh_dashboard(); self.refresh_shooters(); "
    "self.refresh_standings(); self.refresh_projection_shooters(); "
    "self.refresh_snapshots(); self.refresh_imports()"
)
new_refresh = (
    "def refresh_all(self): self.refresh_dashboard(); self.refresh_race(); "
    "self.refresh_shooters(); self.refresh_standings(); "
    "self.refresh_projection_shooters(); self.refresh_snapshots(); "
    "self.refresh_imports()"
)

old_refresh_progress = (
    "def refresh_all(self): self.refresh_dashboard(); self.refresh_progress(); "
    "self.refresh_shooters(); self.refresh_standings(); "
    "self.refresh_projection_shooters(); self.refresh_snapshots(); "
    "self.refresh_imports()"
)
new_refresh_progress = (
    "def refresh_all(self): self.refresh_dashboard(); self.refresh_progress(); "
    "self.refresh_race(); self.refresh_shooters(); self.refresh_standings(); "
    "self.refresh_projection_shooters(); self.refresh_snapshots(); "
    "self.refresh_imports()"
)

if old_refresh_progress in text:
    text = text.replace(old_refresh_progress, new_refresh_progress)
elif old_refresh in text:
    text = text.replace(old_refresh, new_refresh)
elif "self.refresh_race()" not in text:
    raise RuntimeError("Could not locate refresh_all")

refresh_method = '''    def refresh_race(self):
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
'''

if "    def refresh_race(self):" not in text:
    marker = "    def refresh_dashboard(self):"
    if marker not in text:
        raise RuntimeError("Could not locate refresh_dashboard")
    text = text.replace(marker, refresh_method + marker)

for old in ("MNTrapTeam 1.5", "MNTrapTeam 1.6", "MNTrapTeam 1.7", "MNTrapTeam 1.8"):
    text = text.replace(old, "MNTrapTeam 1.9")

gui_path.write_text(text, encoding="utf-8")
Path("VERSION").write_text("1.9.0\n", encoding="utf-8")
print("MNTrapTeam 1.9.0 Team Race dashboard applied.")
