from pathlib import Path
import re

version = "2.4.0"
Path("VERSION").write_text(version + "\n", encoding="utf-8")

init = Path("mntrapteam/__init__.py")
text = init.read_text(encoding="utf-8") if init.exists() else ""
if re.search(r'__version__\s*=', text):
    text = re.sub(
        r'__version__\s*=\s*["\'][^"\']+["\']',
        f'__version__ = "{version}"',
        text,
        count=1,
    )
else:
    text = text.rstrip() + f'\n\n__version__ = "{version}"\n'
init.write_text(text, encoding="utf-8")

gui = Path("mntrapteam/gui.py")
if gui.exists():
    gui_text = gui.read_text(encoding="utf-8")
    gui_text = re.sub(
        r"self\.setWindowTitle\('MNTrapTeam [^']+'\)",
        f"self.setWindowTitle('MNTrapTeam {version}')",
        gui_text,
        count=1,
    )
    gui.write_text(gui_text, encoding="utf-8")

print("MNTrapTeam 2.4.0 real-data importer installed.")
