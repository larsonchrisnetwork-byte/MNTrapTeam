import sys, json
from PySide6.QtWidgets import QApplication
from .paths import CONFIG, ROOT
from .database import Database
from .rules import RulesEngine
from .gui import MainWindow

def run():
    settings=json.loads((CONFIG/'settings.json').read_text(encoding='utf-8-sig'))
    db=Database(ROOT/settings['database']); app=QApplication(sys.argv); app.setApplicationName('MNTrapTeam'); app.setOrganizationName('MNTrapTeam')
    win=MainWindow(db,RulesEngine(),settings); win.show(); return app.exec()
