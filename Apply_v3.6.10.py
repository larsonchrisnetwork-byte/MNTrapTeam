from pathlib import Path
import re

VERSION = "3.6.10"
TARGET = Path("mntrapteam/myata_bulk_dom_cli.py")
OLD = '        if (\n            not refresh\n            and str(item.get("existing_source") or "").lower().startswith(\n                "myata official rendered detail"\n            )\n        ):\n            continue\n'
NEW = '        source = str(item.get("existing_source") or "").strip().lower()\n\n        if not refresh and source.startswith("myata"):\n            # Any existing MyATA baseline is already an official ATA source.\n            # This includes the logged-in user, whose earlier MyATA capture\n            # may use a different source label than the rendered bulk scraper.\n            continue\n'

def main():
    if not TARGET.exists():
        raise SystemExit("Run from H:\\MNTrapTeam\\MNTrapTeam")

    text = TARGET.read_text(encoding="utf-8")

    if OLD in text:
        text = text.replace(OLD, NEW, 1)
    elif NEW not in text:
        raise RuntimeError("Could not find v3.6.9 MyATA resume filter.")

    compile(text, str(TARGET), "exec")
    TARGET.write_text(text, encoding="utf-8")

    Path("VERSION").write_text(VERSION + "\n", encoding="utf-8")

    gui = Path("mntrapteam/gui.py")
    if gui.exists():
        g = gui.read_text(encoding="utf-8")
        g = re.sub(
            r"MNTrapTeam \d+\.\d+\.\d+",
            f"MNTrapTeam {VERSION}",
            g,
            count=1,
        )
        gui.write_text(g, encoding="utf-8")

    init = Path("mntrapteam/__init__.py")
    if init.exists():
        lines = init.read_text(encoding="utf-8").splitlines()
        found = False
        for index, line in enumerate(lines):
            if line.strip().startswith("__version__"):
                lines[index] = f'__version__ = "{VERSION}"'
                found = True
                break
        if not found:
            lines.append(f'__version__ = "{VERSION}"')
        init.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(
        "MNTrapTeam 3.6.10 applied: resume skips any existing MyATA baseline."
    )

if __name__ == "__main__":
    main()
