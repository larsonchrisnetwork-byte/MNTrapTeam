from pathlib import Path
import re

VERSION = "3.0.0"
GUI = Path("mntrapteam/gui.py")


def main():
    if not GUI.exists():
        raise SystemExit("Run from the MNTrapTeam repository root.")

    text = GUI.read_text(encoding="utf-8")
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
    print("MNTrapTeam 3.0.0 source-aware reconciliation engine applied.")


if __name__ == "__main__":
    main()
