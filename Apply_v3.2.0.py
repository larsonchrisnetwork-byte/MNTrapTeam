from pathlib import Path
import re

VERSION = "3.2.0"
GUI = Path("mntrapteam/gui.py")
METHOD_TEXT = '\n    def make_live_team(self):\n        w=QWidget()\n        v=QVBoxLayout(w)\n        note=QLabel(\n            "Primary current-year team view. HAA-qualified shooters appear "\n            "first. Live totals use fast sources when available; official "\n            "totals use MyATA-confirmed observations."\n        )\n        note.setWordWrap(True)\n        v.addWidget(note)\n\n        controls=QHBoxLayout()\n        self.live_team_box=QComboBox()\n        self.live_team_box.addItems(self.rules.rules["teams"])\n        if self.live_team_box.findText("MEN") >= 0:\n            self.live_team_box.setCurrentText("MEN")\n        self.live_team_box.currentTextChanged.connect(self.refresh_live_team)\n        controls.addWidget(QLabel("Team"))\n        controls.addWidget(self.live_team_box)\n\n        refresh=QPushButton("Refresh live race")\n        refresh.clicked.connect(self.refresh_live_team)\n        controls.addWidget(refresh)\n\n        mine=QPushButton("Show my row")\n        mine.clicked.connect(self.show_my_live_row)\n        controls.addWidget(mine)\n        controls.addStretch()\n        v.addLayout(controls)\n\n        self.live_cards=QLabel()\n        self.live_cards.setTextFormat(Qt.RichText)\n        self.live_cards.setWordWrap(True)\n        self.live_cards.setMinimumHeight(100)\n        v.addWidget(self.live_cards)\n\n        self.live_table=QTableView()\n        self.live_table.setAlternatingRowColors(True)\n        self.live_table.setSelectionBehavior(QAbstractItemView.SelectRows)\n        v.addWidget(self.live_table)\n\n        self.tabs.addTab(w,"2026 Live Team")\n        return w\n\n    def refresh_live_team(self):\n        if not hasattr(self,"live_team_box"):\n            return\n        team=self.live_team_box.currentText() or "MEN"\n        result=live_team_rows(self.db,self.ts,self.season,team)\n        summary=result["summary"]\n        cut=summary["live_cut_hoa"]\n        cut_text="Not established" if cut is None else f"{cut:.2f}%"\n\n        self.live_cards.setText(\n            f"<h2>{self.season} {team} Live Team Race</h2>"\n            f"<b>{summary[\'haa_qualified\']}</b> HAA-qualified &nbsp;&nbsp; "\n            f"<b>{summary[\'eligible_qualified\']}</b> fully eligible &nbsp;&nbsp; "\n            f"<b>{summary[\'selected\']}/{summary[\'team_size\']}</b> positions &nbsp;&nbsp; "\n            f"<b>Live cut:</b> {cut_text}<br>"\n            f"<b>{summary[\'observation_shooters\']}</b> shooters with source observations &nbsp;&nbsp; "\n            f"<b>{summary[\'pending_targets\']:,}</b> targets pending official confirmation &nbsp;&nbsp; "\n            f"<b>{summary[\'disputed_targets\']:,}</b> disputed targets"\n        )\n\n        self.live_table.setModel(\n            DictModel(\n                result["rows"],\n                [\n                    ("live_pool_rank","Pool Rank"),\n                    ("live_team","Team"),\n                    ("haa_gate","HAA Gate"),\n                    ("haa_route","HAA Route"),\n                    ("eligible","All Eligible"),\n                    ("display_name","Shooter"),\n                    ("ata_number","ATA #"),\n                    ("live_hoa","Live HOA"),\n                    ("official_hoa","Official HOA"),\n                    ("hoa_delta","Live - Official"),\n                    ("live_cut_hoa","Cut"),\n                    ("live_gap_to_cut","Gap"),\n                    ("pending_targets","Pending"),\n                    ("disputed_targets","Disputed"),\n                    ("live_singles_targets","Live Singles"),\n                    ("live_handicap_targets","Live Handicap"),\n                    ("live_doubles_targets","Live Doubles"),\n                    ("mn_clubs","MN Clubs"),\n                    ("eligibility_reasons_text","Missing Requirements"),\n                    ("live_source","Live Data Source"),\n                ],\n            )\n        )\n        self.live_table.resizeColumnsToContents()\n\n    def show_my_live_row(self):\n        ata=(\n            self.user_ata.text()\n            if hasattr(self,"user_ata")\n            else self.settings.get("user_ata_number","")\n        )\n        result=live_dashboard_for_ata(\n            self.db,\n            self.ts,\n            self.season,\n            ata,\n            self.live_team_box.currentText() or "MEN",\n        )\n        shooter=result.get("shooter")\n        if not shooter:\n            QMessageBox.information(\n                self,\n                "My live row",\n                "Your ATA number was not found in the current live team rows.",\n            )\n            return\n\n        gap=shooter.get("live_gap_to_cut")\n        gap_text="Not established" if gap is None else f"{gap:+.2f}"\n        message=(\n            f"{shooter[\'display_name\']}\\n"\n            f"HAA: {shooter[\'haa_gate\']} {shooter[\'haa_route\']}\\n"\n            f"Eligible: {\'Yes\' if shooter.get(\'eligible\') else \'No\'}\\n"\n            f"Live HOA: {shooter[\'live_hoa\']:.2f}%\\n"\n            f"Official HOA: {shooter[\'official_hoa\']:.2f}%\\n"\n            f"Pending targets: {shooter[\'pending_targets\']}\\n"\n            f"Gap to live cut: {gap_text}"\n        )\n        QMessageBox.information(self,"My live team position",message)\n\n'


def main():
    if not GUI.exists():
        raise SystemExit("Run from the MNTrapTeam repository root.")

    text = GUI.read_text(encoding="utf-8")

    import_line = (
        "from .live_dashboard import "
        "live_team_rows, live_dashboard_for_ata"
    )
    if import_line not in text:
        anchor = "from .race_changes import race_changes_from_latest_snapshot"
        if anchor not in text:
            raise RuntimeError("Could not find GUI import anchor")
        text = text.replace(anchor, anchor + "\n" + import_line, 1)

    constructor_anchor = (
        "self.dashboard=self.make_dashboard(); "
        "self.progress=self.make_progress();"
    )
    constructor_replacement = (
        "self.dashboard=self.make_dashboard(); "
        "self.live_team=self.make_live_team(); "
        "self.progress=self.make_progress();"
    )
    if (
        "self.live_team=self.make_live_team()" not in text
        and constructor_anchor in text
    ):
        text = text.replace(
            constructor_anchor,
            constructor_replacement,
            1,
        )

    if "def make_live_team(self):" not in text:
        method_anchor = "    def make_shooters(self):"
        if method_anchor not in text:
            raise RuntimeError("Could not find GUI method anchor")
        text = text.replace(
            method_anchor,
            METHOD_TEXT + method_anchor,
            1,
        )

    refresh_anchor = (
        "def refresh_all(self): self.refresh_dashboard();"
    )
    refresh_replacement = (
        "def refresh_all(self): self.refresh_dashboard(); "
        "self.refresh_live_team();"
    )
    if (
        "self.refresh_live_team();" not in text
        and refresh_anchor in text
    ):
        text = text.replace(
            refresh_anchor,
            refresh_replacement,
            1,
        )

    text = re.sub(
        r"self\.setWindowTitle\('MNTrapTeam [^']+'\)",
        f"self.setWindowTitle('MNTrapTeam {VERSION}')",
        text,
        count=1,
    )

    compile(text, str(GUI), "exec")
    GUI.write_text(text, encoding="utf-8")
    Path("VERSION").write_text(VERSION + "\n", encoding="utf-8")

    init = Path("mntrapteam/__init__.py")
    value = init.read_text(encoding="utf-8") if init.exists() else ""
    if re.search(r'__version__\s*=', value):
        value = re.sub(
            r'__version__\s*=\s*["\'][^"\']+["\']',
            f'__version__ = "{VERSION}"',
            value,
            count=1,
        )
    else:
        value = value.rstrip() + f'\n\n__version__ = "{VERSION}"\n'
    init.write_text(value, encoding="utf-8")

    print("MNTrapTeam 3.2.0 usable live team dashboard applied.")


if __name__ == "__main__":
    main()
