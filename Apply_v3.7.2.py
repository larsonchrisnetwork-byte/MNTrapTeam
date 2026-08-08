from pathlib import Path
import re

VERSION = "3.7.2"
ENRICH = Path("mntrapteam/myata_mn_enrichment.py")
CLI = Path("mntrapteam/myata_mn_enrich_cli.py")


def patch_aliases():
    if not ENRICH.exists():
        raise RuntimeError("Missing mntrapteam/myata_mn_enrichment.py")

    text = ENRICH.read_text(encoding="utf-8")

    additions = {
        "OWATONNA GUN CLUB": {
            "club_id": "MN-OWATONNA",
            "name": "Owatonna Gun Club",
            "state": "MN",
        },
        "MINNEAPOLIS GUN CLUB": {
            "club_id": "MN-MINNEAPOLIS",
            "name": "Minneapolis Gun Club",
            "state": "MN",
        },
    }

    marker = "MN_CLUB_ALIASES = {"
    if marker not in text:
        raise RuntimeError("MN_CLUB_ALIASES table not found. Apply v3.7.1 first.")

    for key, value in additions.items():
        if f'"{key}"' in text:
            continue

        insertion = (
            f'    "{key}": '
            + "{"
            + f'"club_id":"{value["club_id"]}",'
            + f'"name":"{value["name"]}",'
            + f'"state":"{value["state"]}"'
            + "},\n"
        )

        close = text.find("}\n", text.find(marker))
        if close == -1:
            raise RuntimeError("Could not locate MN_CLUB_ALIASES closing brace.")

        text = text[:close] + insertion + text[close:]

    compile(text, str(ENRICH), "exec")
    ENRICH.write_text(text, encoding="utf-8")


def patch_default_limit():
    if not CLI.exists():
        raise RuntimeError("Missing mntrapteam/myata_mn_enrich_cli.py")

    text = CLI.read_text(encoding="utf-8")

    old = '    parser.add_argument("--limit", type=int, default=25)\n'
    new = '    parser.add_argument("--limit", type=int, default=None)\n'

    if old in text:
        text = text.replace(old, new, 1)
    elif new not in text:
        raise RuntimeError("Could not find --limit argument.")

    compile(text, str(CLI), "exec")
    CLI.write_text(text, encoding="utf-8")


def update_version():
    Path("VERSION").write_text(VERSION + "\n", encoding="utf-8")

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

    init = Path("mntrapteam/__init__.py")
    if init.exists():
        lines = init.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if line.strip().startswith("__version__"):
                lines[i] = f'__version__ = "{VERSION}"'
                break
        else:
            lines.append(f'__version__ = "{VERSION}"')
        init.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    patch_aliases()
    patch_default_limit()
    update_version()

    print(
        "MNTrapTeam 3.7.2 applied: Owatonna and Minneapolis Gun Club "
        "added as MN clubs; enrichment default is now ALL shooters."
    )


if __name__ == "__main__":
    main()
