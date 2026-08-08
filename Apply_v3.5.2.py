from pathlib import Path
import re

VERSION = "3.5.2"


def main():
    gui = Path("mntrapteam/gui.py")
    if gui.exists():
        text = gui.read_text(encoding="utf-8")
        text = re.sub(
            r"MNTrapTeam \d+\.\d+\.\d+",
            f"MNTrapTeam {VERSION}",
            text,
            count=1,
        )
        gui.write_text(text, encoding="utf-8")

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
    print("MNTrapTeam 3.5.2 SOS State HAA importer applied.")


if __name__ == "__main__":
    main()
