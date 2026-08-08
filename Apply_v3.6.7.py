from pathlib import Path
import re

VERSION = "3.6.7"
TARGET = Path("mntrapteam/myata_bulk_dom_cli.py")

NEW_SEARCH = 'def _find_result_button(page, name):\n    parts = [part for part in re.split(r"\\s+", str(name).strip()) if part]\n    if not parts:\n        return None\n\n    first = parts[0].upper()\n    last = parts[-1].upper()\n\n    buttons = page.locator("button")\n    for index in range(buttons.count()):\n        button = buttons.nth(index)\n        try:\n            text = " ".join(button.inner_text(timeout=500).split()).upper()\n        except Exception:\n            continue\n\n        # MyATA result example:\n        # WEBER, AIDEN KENITH. - MONTICELLO, MN\n        if first in text and last in text:\n            return button\n\n    return None\n\n\ndef _search_and_open(page, ata, name, manual_assist=False):\n    baseline_count = _yearly_summary_count(page)\n\n    _open_search(page)\n    page.wait_for_timeout(600)\n\n    # Search/Buddies is a custom web component. Rather than assuming one\n    # particular input, try each usable input inside the ATA component and\n    # accept only the input that produces the expected shooter result button.\n    candidates = page.locator("ata-shooter-information-center input")\n\n    if candidates.count() == 0:\n        candidates = page.locator("input")\n\n    for index in range(candidates.count()):\n        field = candidates.nth(index)\n\n        try:\n            if not field.is_visible() or field.is_disabled():\n                continue\n        except Exception:\n            continue\n\n        try:\n            field.click(timeout=1500)\n            field.fill("")\n            field.fill(ata)\n            page.wait_for_timeout(900)\n\n            result = _find_result_button(page, name)\n\n            if result is None:\n                try:\n                    field.press("Enter")\n                    page.wait_for_timeout(700)\n                except Exception:\n                    pass\n                result = _find_result_button(page, name)\n\n            if result is None:\n                try:\n                    field.fill("")\n                except Exception:\n                    pass\n                continue\n\n            try:\n                result.click(timeout=5000)\n            except Exception:\n                result.evaluate("(el) => el.click()")\n\n            page.wait_for_timeout(1000)\n\n            if _wait_for_new_yearly_summary(\n                page,\n                baseline_count,\n                timeout_ms=7000,\n            ):\n                return True\n\n        except Exception:\n            continue\n\n    if manual_assist:\n        print()\n        print(f"  Automatic ATA search failed for {name}.")\n        print("  The browser will remain open.")\n        print(f"  In Search/Buddies, manually search ATA {ata}.")\n        print(f"  Click the result for {name}.")\n        print("  Leave that shooter\'s Yearly Summary visible.")\n        input("  Then return here and press Enter... ")\n\n        if _wait_for_new_yearly_summary(\n            page,\n            baseline_count,\n            timeout_ms=3000,\n        ):\n            return True\n\n    return False\n'
NEW_OPEN_YEAR = 'def _open_year_detail(page, year, manual_assist=False):\n    table = _searched_yearly_table(page)\n    rows = table.locator("tr")\n\n    for index in range(rows.count()):\n        row = rows.nth(index)\n        cells = [\n            " ".join(x.split())\n            for x in row.locator("th,td").all_inner_texts()\n        ]\n\n        if not cells or cells[0] != str(year):\n            continue\n\n        year_cell = row.locator("th,td").first\n\n        try:\n            year_cell.click(timeout=5000, force=True)\n        except Exception:\n            try:\n                year_cell.evaluate("(el) => el.click()")\n            except Exception:\n                row.evaluate("(el) => el.click()")\n\n        page.wait_for_timeout(1000)\n\n        try:\n            _score_detail_table(page, year)\n            return cells\n        except Exception:\n            pass\n\n        if manual_assist:\n            print()\n            print(f"  Automatic {year} detail-open failed.")\n            print(f"  In the browser, click {year} so that")\n            print(f"  {year} Score Details is visible.")\n            input("  Then return here and press Enter... ")\n\n            try:\n                _score_detail_table(page, year)\n                return cells\n            except Exception:\n                pass\n\n        raise RuntimeError(\n            f"{year} summary found, but {year} Score Details did not open"\n        )\n\n    raise RuntimeError(\n        f"Year {year} row not found in searched shooter summary"\n    )\n'
NEW_SCRAPE = 'def _scrape(page, year, manual_assist=False):\n    summary_cells = _open_year_detail(\n        page,\n        year,\n        manual_assist=manual_assist,\n    )\n    summary = parse_year_summary_row(summary_cells)\n\n    detail = _score_detail_table(page, year)\n    totals = parse_score_detail_rows(_table_rows(detail))\n    warnings = validate_detail_against_summary(totals, summary)\n    return totals, warnings\n'

def replace_function(text, function_name, new_code):
    pattern = re.compile(
        rf"(?ms)^def {re.escape(function_name)}\(.*?(?=^def |^if __name__|\Z)"
    )
    match = pattern.search(text)
    if not match:
        raise RuntimeError(f"Could not find {function_name}().")
    return text[:match.start()] + new_code + "\n\n" + text[match.end():]

def main():
    if not TARGET.exists():
        raise SystemExit("Run from H:\\MNTrapTeam\\MNTrapTeam")

    text = TARGET.read_text(encoding="utf-8")

    text = replace_function(text, "_search_and_open", NEW_SEARCH)
    text = replace_function(text, "_open_year_detail", NEW_OPEN_YEAR)
    text = replace_function(text, "_scrape", NEW_SCRAPE)

    old_call = '                totals, warnings = _scrape(page, args.season)\n'
    new_call = '                totals, warnings = _scrape(\n                    page,\n                    args.season,\n                    manual_assist=args.manual_assist,\n                )\n'

    if old_call in text:
        text = text.replace(old_call, new_call, 1)
    elif new_call not in text:
        raise RuntimeError("Could not update _scrape() call.")

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
        "MNTrapTeam 3.6.7 applied: ATA Search/Buddies result selection fixed."
    )

if __name__ == "__main__":
    main()
