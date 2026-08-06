from __future__ import annotations

from pathlib import Path
import re

GUI = Path("mntrapteam/gui.py")


def insert_after(text, anchor, addition):
    if addition.strip() in text:
        return text
    if anchor not in text:
        raise RuntimeError(f"Missing anchor: {anchor}")
    return text.replace(anchor, anchor + addition, 1)


def insert_before(text, anchor, addition):
    if addition.strip() in text:
        return text
    if anchor not in text:
        raise RuntimeError(f"Missing anchor: {anchor}")
    return text.replace(anchor, addition + anchor, 1)


MAKE_TAB = '''
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

'''

REFRESH = '''
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

'''


def replace_tabs(text):
    marker = "self.settings_tab=self.make_settings()"
    if "self.event_intelligence=self.make_event_intelligence()" in text:
        return text
    if marker not in text:
        raise RuntimeError("Could not find tab initialization")
    return text.replace(
        marker,
        "self.event_intelligence=self.make_event_intelligence(); " + marker,
        1,
    )


def replace_refresh_all(text):
    pattern = r"    def refresh_all\(self\):[^\n]*"
    match = re.search(pattern, text)
    if not match:
        raise RuntimeError("Could not find refresh_all")
    line = match.group(0)
    if "self.refresh_event_shooters()" not in line:
        line = line.rstrip() + "; self.refresh_event_shooters(); self.refresh_event_intelligence()"
    return text[:match.start()] + line + text[match.end():]


def main():
    if not GUI.exists():
        raise SystemExit("Run from the MNTrapTeam repository root.")

    text=GUI.read_text(encoding='utf-8')
    if "from .event_intelligence import event_intelligence" not in text:
        preferred="from .race import team_race"
        fallback="from .sample_data import load as load_sample"
        anchor=preferred if preferred in text else fallback
        text=insert_after(
            text,
            anchor,
            "\nfrom .event_intelligence import event_intelligence",
        )

    text=replace_tabs(text)
    text=insert_before(text,"    def make_shooters(self):",MAKE_TAB)
    text=insert_before(text,"    def refresh_dashboard(self):",REFRESH)
    text=replace_refresh_all(text)
    text=re.sub(
        r"self\.setWindowTitle\('MNTrapTeam [^']+'\)",
        "self.setWindowTitle('MNTrapTeam 2.1.0')",
        text,
        count=1,
    )

    compile(text,str(GUI),'exec')
    GUI.write_text(text,encoding='utf-8')
    Path("VERSION").write_text("2.1.0\n",encoding='utf-8')
    print("MNTrapTeam 2.1.0 Event Intelligence applied.")


if __name__=="__main__":
    main()
