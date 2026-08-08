from pathlib import Path
import re

VERSION = "3.6.9"
TARGET = Path("mntrapteam/myata_bulk_dom_cli.py")

OLD_CANDIDATES = 'def _candidates(db, season, limit):\n    rows = db.query(\n        """\n        SELECT DISTINCT s.id,s.ata_number,s.display_name\n        FROM haa_qualifications h\n        JOIN shooters s ON s.id=h.shooter_id\n        WHERE h.season=?\n          AND h.verified=1\n          AND s.ata_number IS NOT NULL\n          AND trim(s.ata_number)<>\'\'\n        ORDER BY s.display_name\n        """,\n        (season,),\n    )\n    values = [dict(row) for row in rows]\n    return values[:limit] if limit else values\n'
NEW_CANDIDATES = 'def _candidates(db, season, limit, *, refresh=False):\n    rows = db.query(\n        """\n        SELECT DISTINCT\n            s.id,\n            s.ata_number,\n            s.display_name,\n            COALESCE(st.source, \'\') AS existing_source\n        FROM haa_qualifications h\n        JOIN shooters s ON s.id=h.shooter_id\n        LEFT JOIN season_stats st\n          ON st.shooter_id=s.id\n         AND st.season=h.season\n        WHERE h.season=?\n          AND h.verified=1\n          AND s.ata_number IS NOT NULL\n          AND trim(s.ata_number)<>\'\'\n        ORDER BY s.display_name\n        """,\n        (season,),\n    )\n\n    values = []\n    for row in rows:\n        item = dict(row)\n        if (\n            not refresh\n            and str(item.get("existing_source") or "").lower().startswith(\n                "myata official rendered detail"\n            )\n        ):\n            continue\n        values.append(item)\n\n    return values[:limit] if limit else values\n'
HELPERS = 'def _load_settings():\n    import json\n    path = Path("config/settings.json")\n    if not path.exists():\n        return {}\n    text = path.read_text(encoding="utf-8-sig")\n    return json.loads(text) if text.strip() else {}\n\n\ndef _normalized_ata(value):\n    return "".join(\n        character for character in str(value or "")\n        if character.isdigit()\n    )\n\n\ndef _self_ata_number():\n    settings = _load_settings()\n    return _normalized_ata(settings.get("user_ata_number"))\n\n\ndef _self_yearly_table(page):\n    tables = _yearly_tables(page)\n    if not tables:\n        raise RuntimeError("Logged-in MyATA Yearly Summary is not available")\n    return tables[0]\n\n\ndef _open_self_year_detail(page, year, manual_assist=False):\n    table = _self_yearly_table(page)\n    rows = table.locator("tr")\n\n    for index in range(rows.count()):\n        row = rows.nth(index)\n        cells = [\n            " ".join(x.split())\n            for x in row.locator("th,td").all_inner_texts()\n        ]\n        if not cells or cells[0] != str(year):\n            continue\n\n        cell = row.locator("th,td").first\n        try:\n            cell.click(timeout=5000, force=True)\n        except Exception:\n            try:\n                cell.evaluate("(el) => el.click()")\n            except Exception:\n                row.evaluate("(el) => el.click()")\n\n        page.wait_for_timeout(1000)\n        try:\n            detail = _score_detail_table(page, year)\n            return cells, detail\n        except Exception:\n            pass\n\n        if manual_assist:\n            print()\n            print(f"  Automatic My Scores {year} detail-open failed.")\n            print(f"  In the browser, click your {year} row so that")\n            print(f"  {year} Score Details is visible.")\n            input("  Then return here and press Enter... ")\n            detail = _score_detail_table(page, year)\n            return cells, detail\n\n        raise RuntimeError(\n            f"Logged-in {year} summary found, but Score Details did not open"\n        )\n\n    raise RuntimeError(f"Year {year} not found in logged-in MyATA summary")\n\n\ndef _scrape_self(page, year, manual_assist=False):\n    summary_cells, detail = _open_self_year_detail(\n        page,\n        year,\n        manual_assist=manual_assist,\n    )\n    summary = parse_year_summary_row(summary_cells)\n    totals = parse_score_detail_rows(_table_rows(detail))\n    warnings = validate_detail_against_summary(totals, summary)\n    return totals, warnings\n'
OLD_LOOP = '                opened = _search_and_open(\n                    page,\n                    ata,\n                    name,\n                    manual_assist=args.manual_assist,\n                )\n                if not opened:\n                    raise RuntimeError(\n                        "Search result was not opened; no Yearly Summary appeared"\n                    )\n\n                totals, warnings = _scrape(\n                    page,\n                    args.season,\n                    manual_assist=args.manual_assist,\n                )\n'
NEW_LOOP = '                self_ata = _self_ata_number()\n\n                if self_ata and _normalized_ata(ata) == self_ata:\n                    print("  Using logged-in My Scores record.")\n                    totals, warnings = _scrape_self(\n                        page,\n                        args.season,\n                        manual_assist=args.manual_assist,\n                    )\n                else:\n                    opened = _search_and_open(\n                        page,\n                        ata,\n                        name,\n                        manual_assist=args.manual_assist,\n                    )\n                    if not opened:\n                        raise RuntimeError(\n                            "Search result was not opened; no new Yearly Summary appeared"\n                        )\n\n                    totals, warnings = _scrape(\n                        page,\n                        args.season,\n                        manual_assist=args.manual_assist,\n                    )\n'

def main():
    if not TARGET.exists():
        raise SystemExit("Run from H:\\MNTrapTeam\\MNTrapTeam")

    text = TARGET.read_text(encoding="utf-8")

    if OLD_CANDIDATES in text:
        text = text.replace(OLD_CANDIDATES, NEW_CANDIDATES, 1)
    elif NEW_CANDIDATES not in text:
        raise RuntimeError("Could not find _candidates() block.")

    marker = "def _find_result_button(page, name):\n"
    if "_scrape_self(" not in text:
        if marker not in text:
            raise RuntimeError("Could not find helper insertion point.")
        text = text.replace(marker, HELPERS + "\n\n" + marker, 1)

    arg_marker = '    parser.add_argument("--dry-run", action="store_true")\n'
    if '--refresh' not in text:
        addition = (
            arg_marker
            + '    parser.add_argument(\n'
            + '        "--refresh",\n'
            + '        action="store_true",\n'
            + '        help="Re-import shooters with an existing rendered MyATA baseline",\n'
            + '    )\n'
        )
        if arg_marker not in text:
            raise RuntimeError("Could not add --refresh argument.")
        text = text.replace(arg_marker, addition, 1)

    old_call = '    shooters = _candidates(db, args.season, args.limit)\n'
    new_call = (
        '    shooters = _candidates(\n'
        '        db,\n'
        '        args.season,\n'
        '        args.limit,\n'
        '        refresh=args.refresh,\n'
        '    )\n'
    )
    if old_call in text:
        text = text.replace(old_call, new_call, 1)
    elif new_call not in text:
        raise RuntimeError("Could not update candidate call.")

    if OLD_LOOP in text:
        text = text.replace(OLD_LOOP, NEW_LOOP, 1)
    elif NEW_LOOP not in text:
        raise RuntimeError("Could not update main scrape loop.")

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
        "MNTrapTeam 3.6.9 applied: skip imported shooters and handle logged-in MyATA user."
    )

if __name__ == "__main__":
    main()
