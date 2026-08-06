from pathlib import Path
import re

VERSION = "2.8.0"
GUI = Path("mntrapteam/gui.py")
REQUIREMENTS = Path("requirements.txt")
GITIGNORE = Path(".gitignore")


def add_line(path: Path, line: str) -> None:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = text.splitlines()
    if line not in lines:
        lines.append(line)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main():
    if not GUI.exists():
        raise SystemExit("Run from the MNTrapTeam repository root.")

    add_line(REQUIREMENTS, "playwright>=1.50")
    add_line(GITIGNORE, "data/browser_sessions/")
    add_line(GITIGNORE, "data/connector_downloads/")
    add_line(GITIGNORE, "data/connector_traces/")

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

    print("MNTrapTeam 2.8.0 secure connector foundation applied.")
    print("Next run Install_MNTrapTeam.bat, then install Chromium for Playwright.")


if __name__ == "__main__":
    main()
