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

'''

REFRESH = '''
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

'''


def replace_tabs(text):
    marker = "self.settings_tab=self.make_settings()"
    if "self.race_changes=self.make_race_changes()" in text:
        return text
    if marker not in text:
        raise RuntimeError("Could not find tab initialization")
    return text.replace(
        marker,
        "self.race_changes=self.make_race_changes(); " + marker,
        1,
    )


def replace_refresh_all(text):
    pattern = r"    def refresh_all\(self\):[^\n]*"
    match = re.search(pattern, text)
    if not match:
        raise RuntimeError("Could not find refresh_all")
    line = match.group(0)
    if "self.refresh_race_changes()" not in line:
        line = line.rstrip() + "; self.refresh_race_changes()"
    return text[:match.start()] + line + text[match.end():]


def main():
    if not GUI.exists():
        raise SystemExit("Run from the MNTrapTeam repository root.")

    text = GUI.read_text(encoding="utf-8")
    if "from .race_changes import race_changes_from_latest_snapshot" not in text:
        preferred = "from .event_intelligence import event_intelligence"
        fallback = "from .race import team_race"
        anchor = preferred if preferred in text else fallback
        text = insert_after(
            text,
            anchor,
            "\nfrom .race_changes import race_changes_from_latest_snapshot",
        )

    text = replace_tabs(text)
    text = insert_before(text, "    def make_shooters(self):", MAKE_TAB)
    text = insert_before(text, "    def refresh_dashboard(self):", REFRESH)
    text = replace_refresh_all(text)
    text = re.sub(
        r"self\.setWindowTitle\('MNTrapTeam [^']+'\)",
        "self.setWindowTitle('MNTrapTeam 2.2.0')",
        text,
        count=1,
    )

    compile(text, str(GUI), "exec")
    GUI.write_text(text, encoding="utf-8")
    Path("VERSION").write_text("2.2.0\n", encoding="utf-8")
    print("MNTrapTeam 2.2.0 Race Changes applied.")


if __name__ == "__main__":
    main()
