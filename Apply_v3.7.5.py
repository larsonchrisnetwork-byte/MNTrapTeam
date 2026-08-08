from pathlib import Path
import re

VERSION = "3.7.5"
ENRICH = Path("mntrapteam/myata_mn_enrichment.py")
CLI = Path("mntrapteam/myata_mn_enrich_cli.py")

OLD_INIT = '    def __init__(self, rows: list[dict[str, Any]]):\n        self.rows = []\n        self.by_normalized: dict[str, list[dict[str, Any]]] = {}\n'
NEW_INIT = '    def __init__(self, rows: list[dict[str, Any]]):\n        self.rows = []\n        self.by_normalized: dict[str, list[dict[str, Any]]] = {}\n        self.mn_aliases = {\n            normalize_club_name(key): value\n            for key, value in MN_CLUB_ALIASES.items()\n        }\n'
OLD_ALIAS = '        alias = MN_CLUB_ALIASES.get(normalized)\n        if alias:\n'
NEW_ALIAS = '        alias = self.mn_aliases.get(normalized)\n        if alias:\n'
OLD_BLOCK = '                opened = _search_and_open(\n                    page,\n                    ata,\n                    name,\n                    manual_assist=args.manual_assist,\n                )\n\n                if not opened:\n                    raise RuntimeError("Search/Buddies shooter did not open")\n\n                _open_year_detail(\n                    page,\n                    args.season,\n                    manual_assist=args.manual_assist,\n                )\n\n                detail = _score_detail_table(page, args.season)\n                rows = _table_rows(detail)\n'
NEW_BLOCK = '                last_error = None\n                rows = None\n\n                for attempt in range(1, 3):\n                    try:\n                        opened = _search_and_open(\n                            page,\n                            ata,\n                            name,\n                            manual_assist=(\n                                args.manual_assist and attempt == 2\n                            ),\n                        )\n\n                        if not opened:\n                            raise RuntimeError(\n                                "Search/Buddies shooter did not open"\n                            )\n\n                        _open_year_detail(\n                            page,\n                            args.season,\n                            manual_assist=(\n                                args.manual_assist and attempt == 2\n                            ),\n                        )\n\n                        detail = _score_detail_table(\n                            page,\n                            args.season,\n                        )\n                        rows = _table_rows(detail)\n                        break\n\n                    except Exception as exc:\n                        last_error = exc\n\n                        if attempt == 1:\n                            print(f"  Attempt 1 failed: {exc}")\n                            print("  Retrying shooter once...")\n\n                            try:\n                                page.goto(\n                                    MYATA_URL,\n                                    wait_until="domcontentloaded",\n                                    timeout=60000,\n                                )\n                                page.wait_for_timeout(800)\n                            except Exception:\n                                pass\n\n                if rows is None:\n                    raise RuntimeError(\n                        f"Retry failed: {last_error}"\n                    )\n'

def main():
    if not ENRICH.exists() or not CLI.exists():
        raise SystemExit("Run from H:\\MNTrapTeam\\MNTrapTeam")

    text = ENRICH.read_text(encoding="utf-8")

    if OLD_INIT in text:
        text = text.replace(OLD_INIT, NEW_INIT, 1)
    elif NEW_INIT not in text:
        raise RuntimeError("Could not patch SOSClubDirectory.__init__().")

    if OLD_ALIAS in text:
        text = text.replace(OLD_ALIAS, NEW_ALIAS, 1)
    elif NEW_ALIAS not in text:
        raise RuntimeError("Could not patch normalized alias lookup.")

    compile(text, str(ENRICH), "exec")
    ENRICH.write_text(text, encoding="utf-8")

    cli = CLI.read_text(encoding="utf-8")

    if OLD_BLOCK in cli:
        cli = cli.replace(OLD_BLOCK, NEW_BLOCK, 1)
    elif "Retrying shooter once..." not in cli:
        raise RuntimeError("Could not patch enrichment retry block.")

    compile(cli, str(CLI), "exec")
    CLI.write_text(cli, encoding="utf-8")

    Path("VERSION").write_text(VERSION + "\n", encoding="utf-8")

    gui = Path("mntrapteam/gui.py")
    if gui.exists():
        g = gui.read_text(encoding="utf-8")
        g = re.sub(r"MNTrapTeam \d+\.\d+\.\d+", f"MNTrapTeam {VERSION}", g, count=1)
        gui.write_text(g, encoding="utf-8")

    init = Path("mntrapteam/__init__.py")
    if init.exists():
        lines = init.read_text(encoding="utf-8").splitlines()
        for idx, line in enumerate(lines):
            if line.strip().startswith("__version__"):
                lines[idx] = f'__version__ = "{VERSION}"'
                break
        else:
            lines.append(f'__version__ = "{VERSION}"')
        init.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(
        "MNTrapTeam 3.7.5 applied: normalized MTA alias matching "
        "and automatic enrichment retry added."
    )

if __name__ == "__main__":
    main()
