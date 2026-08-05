from pathlib import Path
import re

gui_path = Path("mntrapteam/gui.py")
text = gui_path.read_text(encoding="utf-8")

text = text.replace(
    "from .calculations import project",
    "from .planner import projected_team_rank, required_uniform_average_for_cut",
)

new_make = '''    def make_projections(self):
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
'''

text, count = re.subn(
    r"    def make_projections\(self\):.*?    def make_archive\(self\):",
    new_make + "\n    def make_archive(self):",
    text,
    flags=re.S,
)
if count != 1:
    raise RuntimeError(f"Could not replace make_projections; matches={count}")

new_calc = '''    def _projection_additions(self):
        return {disc:(boxes[0].value(),boxes[1].value()) for disc,boxes in self.proj_inputs.items()}
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
'''

text, count = re.subn(
    r"    def calc_projection\(self\):.*?    def snapshot\(self\):",
    new_calc + "\n    def snapshot(self):",
    text,
    flags=re.S,
)
if count != 1:
    raise RuntimeError(f"Could not replace calc_projection; matches={count}")

text = text.replace("MNTrapTeam 1.3", "MNTrapTeam 1.6")
gui_path.write_text(text, encoding="utf-8")
Path("VERSION").write_text("1.6.0\n", encoding="utf-8")
print("MNTrapTeam 1.6.0 projection planner applied.")
