
from pathlib import Path
gui_path = Path("mntrapteam/gui.py")
text = gui_path.read_text(encoding="utf-8")
text = text.replace(
    "from .importers import OfficialStatsImporter,ScoreboardImporter",
    "from .importers import ScoreboardImporter\nfrom .ingestion import TrackedOfficialStatsImporter,BatchImportService",
)
text = text.replace("OfficialStatsImporter(self.db).import_file", "TrackedOfficialStatsImporter(self.db).import_file")
old = "row=QHBoxLayout(); b1=QPushButton('Import official ShootATA file'); b1.clicked.connect(self.import_official); row.addWidget(b1); b2=QPushButton('Import ShootScoreBoard report'); b2.clicked.connect(self.import_scoreboard); row.addWidget(b2); b3=QPushButton('Open ShootATA login'); b3.clicked.connect(open_shootata_login); row.addWidget(b3); row.addStretch(); v.addLayout(row)"
new = "row=QHBoxLayout(); b1=QPushButton('Import official ShootATA file'); b1.clicked.connect(self.import_official); row.addWidget(b1); b2=QPushButton('Import ShootScoreBoard report'); b2.clicked.connect(self.import_scoreboard); row.addWidget(b2); batch=QPushButton('Import folder'); batch.clicked.connect(self.import_folder); row.addWidget(batch); b3=QPushButton('Open ShootATA login'); b3.clicked.connect(open_shootata_login); row.addWidget(b3); row.addStretch(); v.addLayout(row)"
if old not in text:
    raise RuntimeError("Could not find the Imports button row in gui.py")
text = text.replace(old, new)
marker = "    def calc_projection(self):"
method = "\n".join([
"    def import_folder(self):",
"        folder=QFileDialog.getExistingDirectory(self,'Folder containing import files')",
"        if not folder:return",
"        club,ok=QInputDialog.getText(self,'Club','Default Minnesota club/location for score reports')",
"        if not ok:return",
"        results=BatchImportService(self.db,self.threshold.value()).import_folder(folder,self.season,club=club,in_state=True)",
"        lines=[]",
"        for result in results:",
"            status='ERROR' if result.error else ('DUPLICATE' if result.skipped_duplicate else 'IMPORTED')",
"            lines.append(f\"{status}: {result.path.name} [{result.kind}] {result.rows_imported}/{result.rows_read}\")",
"            if result.error: lines.append(f\"  {result.error}\")",
"            lines.extend(f\"  {warning}\" for warning in result.warnings)",
"        self.import_log.append('Folder import:\\n'+'\\n'.join(lines))",
"        self.refresh_all()",
"",
])
if marker not in text:
    raise RuntimeError("Could not find calc_projection in gui.py")
text = text.replace(marker, method + marker)
text = text.replace("MNTrapTeam 1.3","MNTrapTeam 1.7").replace("MNTrapTeam 1.6","MNTrapTeam 1.7")
gui_path.write_text(text, encoding="utf-8")
Path("VERSION").write_text("1.7.0\n", encoding="utf-8")
print("MNTrapTeam 1.7.0 import pipeline applied.")
