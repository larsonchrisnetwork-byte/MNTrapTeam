from pathlib import Path
import re

VERSION = "3.6.5"
TARGET = Path("mntrapteam/myata_bulk_dom_cli.py")
OLD = 'def _searched_yearly_table(page):\n    tables = _yearly_tables(page)\n    if len(tables) < 2:\n        raise RuntimeError(\n            f"Expected searched-shooter summary in addition to logged-in summary; "\n            f"found {len(tables)} Yearly Summary table(s)"\n        )\n    return tables[-1]\n'
NEW = 'def _searched_yearly_table(page):\n    tables = _yearly_tables(page)\n    if not tables:\n        raise RuntimeError("No Shooter Yearly Summary table is available")\n\n    # _search_and_open() already verifies that the number of summary tables\n    # increased over the pre-search baseline. Depending on MyATA page state,\n    # that can mean 0 -> 1 or 1 -> 2. In either case, the last summary table\n    # is the newly opened searched shooter.\n    return tables[-1]\n'

def main():
    if not TARGET.exists():
        raise SystemExit("Run from H:\\MNTrapTeam\\MNTrapTeam")

    text = TARGET.read_text(encoding="utf-8")

    if OLD in text:
        text = text.replace(OLD, NEW, 1)
    elif NEW not in text:
        raise RuntimeError("Could not find v3.6.4 searched-table block.")

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
        "MNTrapTeam 3.6.5 applied: MyATA 0-to-1 and 1-to-2 "
        "summary-table transitions both supported."
    )

if __name__ == "__main__":
    main()
