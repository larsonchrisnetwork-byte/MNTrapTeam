
from __future__ import annotations

from pathlib import Path
import re

GUI_PATH = Path("mntrapteam/gui.py")


def ensure_once(text: str, anchor: str, addition: str) -> str:
    if addition.strip() in text:
        return text
    if anchor not in text:
        raise RuntimeError(f"Missing expected GUI anchor: {anchor!r}")
    return text.replace(anchor, anchor + addition, 1)


def insert_before_once(text: str, anchor: str, addition: str) -> str:
    if addition.strip() in text:
        return text
    if anchor not in text:
        raise RuntimeError(f"Missing expected GUI anchor: {anchor!r}")
    return text.replace(anchor, addition + anchor, 1)


def replace_tabs(text: str) -> str:
    start_marker = "        self.dashboard=self.make_dashboard();"
    end_marker = "self.settings_tab=self.make_settings()"
    start = text.find(start_marker)
    end = text.find(end_marker, start)
    if start < 0 or end < 0:
        raise RuntimeError("Could not locate tab initialization.")
    end += len(end_marker)
    desired = (
        "        self.dashboard=self.make_dashboard(); "
        "self.progress=self.make_progress(); "
        "self.race=self.make_race(); "
        "self.shooters=self.make_shooters(); "
        "self.imports=self.make_imports(); "
        "self.standings=self.make_standings(); "
        "self.projections=self.make_projections(); "
        "self.archive=self.make_archive(); "
        "self.settings_tab=self.make_settings()"
    )
    return text[:start] + desired + text[end:]


def replace_refresh_all(text: str) -> str:
    pattern = r"    def refresh_all\(self\):[^\n]*"
    replacement = (
        "    def refresh_all(self): "
        "self.refresh_dashboard(); self.refresh_progress(); self.refresh_race(); "
        "self.refresh_shooters(); self.refresh_standings(); "
        "self.refresh_projection_shooters(); self.refresh_snapshots(); "
        "self.refresh_imports()"
    )
    updated, count = re.subn(pattern, replacement, text, count=1)
    if count != 1:
        raise RuntimeError("Could not locate refresh_all.")
    return updated


PROGRESS_METHOD = '''
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

'''

RACE_METHOD = '''
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

'''

REFRESH_PROGRESS = '''
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

'''

REFRESH_RACE = '''
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

'''


def main() -> None:
    if not GUI_PATH.exists():
        raise SystemExit("Run from the MNTrapTeam repository root.")

    text = GUI_PATH.read_text(encoding="utf-8")
    if "from .analytics import personal_progress" not in text:
        text = ensure_once(
            text,
            "from .sample_data import load as load_sample",
            "\nfrom .analytics import personal_progress",
        )
    if "from .race import team_race" not in text:
        text = ensure_once(
            text,
            "from .analytics import personal_progress",
            "\nfrom .race import team_race",
        )

    text = replace_tabs(text)
    text = insert_before_once(text, "    def make_shooters(self):", PROGRESS_METHOD)
    text = insert_before_once(text, "    def make_shooters(self):", RACE_METHOD)
    text = insert_before_once(text, "    def refresh_dashboard(self):", REFRESH_PROGRESS)
    text = insert_before_once(text, "    def refresh_dashboard(self):", REFRESH_RACE)
    text = replace_refresh_all(text)
    text = re.sub(
        r"self\.setWindowTitle\('MNTrapTeam [^']+'\)",
        "self.setWindowTitle('MNTrapTeam 2.0.0')",
        text,
        count=1,
    )

    compile(text, str(GUI_PATH), "exec")
    GUI_PATH.write_text(text, encoding="utf-8")
    Path("VERSION").write_text("2.0.0\n", encoding="utf-8")
    print("MNTrapTeam 2.0.0 consolidation applied.")


if __name__ == "__main__":
    main()
