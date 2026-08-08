from pathlib import Path
import re

VERSION = "3.6.4"
TARGET = Path("mntrapteam/myata_bulk_dom_cli.py")

REPLACEMENTS = [
    ('def _wait_for_yearly_summary(page, timeout_ms=15000):\n    """Wait for MyATA yearly summary through the web component shadow DOM."""\n    try:\n        locator = page.get_by_text("Shooter Yearly Summary", exact=True)\n        locator.first.wait_for(state="visible", timeout=timeout_ms)\n        return True\n    except Exception:\n        pass\n\n    try:\n        import time\n        deadline = time.monotonic() + (timeout_ms / 1000.0)\n        while time.monotonic() < deadline:\n            tables = page.locator("table")\n            for index in range(tables.count()):\n                table = tables.nth(index)\n                try:\n                    if "Shooter Yearly Summary" in table.inner_text(timeout=300):\n                        return True\n                except Exception:\n                    pass\n            page.wait_for_timeout(200)\n    except Exception:\n        pass\n\n    return False\n', 'def _yearly_summary_count(page):\n    count = 0\n    tables = page.locator("table")\n    for index in range(tables.count()):\n        table = tables.nth(index)\n        try:\n            if "Shooter Yearly Summary" in table.inner_text(timeout=300):\n                count += 1\n        except Exception:\n            pass\n    return count\n\n\ndef _wait_for_new_yearly_summary(page, baseline_count, timeout_ms=15000):\n    """Wait until Search/Buddies adds another Yearly Summary table."""\n    import time\n    deadline = time.monotonic() + (timeout_ms / 1000.0)\n    while time.monotonic() < deadline:\n        if _yearly_summary_count(page) > baseline_count:\n            return True\n        page.wait_for_timeout(250)\n    return False\n', "summary wait"),
    ('def _yearly_tables(page):\n    result = []\n    tables = page.locator("table")\n    for index in range(tables.count()):\n        table = tables.nth(index)\n        try:\n            if not table.is_visible():\n                continue\n            table_text = table.inner_text(timeout=800)\n        except Exception:\n            continue\n        if "Shooter Yearly Summary" in table_text:\n            result.append(table)\n    return result\n', 'def _yearly_tables(page):\n    result = []\n    tables = page.locator("table")\n    for index in range(tables.count()):\n        table = tables.nth(index)\n        try:\n            table_text = table.inner_text(timeout=800)\n        except Exception:\n            continue\n        if "Shooter Yearly Summary" in table_text:\n            result.append(table)\n    return result\n', "yearly tables"),
    ('def _searched_yearly_table(page):\n    tables = _yearly_tables(page)\n    if not tables:\n        raise RuntimeError("No visible Shooter Yearly Summary table is available")\n    return tables[-1]\n', 'def _searched_yearly_table(page):\n    tables = _yearly_tables(page)\n    if len(tables) < 2:\n        raise RuntimeError(\n            f"Expected searched-shooter summary in addition to logged-in summary; "\n            f"found {len(tables)} Yearly Summary table(s)"\n        )\n    return tables[-1]\n', "searched table"),
    ('def _score_detail_table(page, year):\n    target = f"{year} Score Details"\n    tables = page.locator("table")\n    result = []\n    for index in range(tables.count()):\n        table = tables.nth(index)\n        try:\n            if not table.is_visible():\n                continue\n            if target in table.inner_text(timeout=800):\n                result.append(table)\n        except Exception:\n            pass\n    if not result:\n        raise RuntimeError(f"No visible {target} table is available")\n    return result[-1]\n', 'def _score_detail_table(page, year):\n    target = f"{year} Score Details"\n    tables = page.locator("table")\n    result = []\n    for index in range(tables.count()):\n        table = tables.nth(index)\n        try:\n            if target in table.inner_text(timeout=800):\n                result.append(table)\n        except Exception:\n            pass\n    if not result:\n        raise RuntimeError(f"No {target} table is available")\n    return result[-1]\n', "score detail table"),
    ('def _open_year_detail(page, year):\n    table = _searched_yearly_table(page)\n    rows = table.locator("tr")\n\n    for index in range(rows.count()):\n        row = rows.nth(index)\n        try:\n            if not row.is_visible():\n                continue\n        except Exception:\n            continue\n\n        cells = [\n            " ".join(x.split())\n            for x in row.locator("th,td").all_inner_texts()\n        ]\n\n        if cells and cells[0] == str(year):\n            try:\n                row.click(timeout=5000)\n            except Exception:\n                row.evaluate("(el) => el.click()")\n            page.wait_for_timeout(1200)\n            return cells\n\n    raise RuntimeError(\n        f"Visible year {year} row not found in searched shooter table"\n    )\n', 'def _open_year_detail(page, year):\n    table = _searched_yearly_table(page)\n    rows = table.locator("tr")\n\n    for index in range(rows.count()):\n        row = rows.nth(index)\n        cells = [\n            " ".join(x.split())\n            for x in row.locator("th,td").all_inner_texts()\n        ]\n\n        if cells and cells[0] == str(year):\n            # Direct DOM click avoids Playwright visibility/stability checks\n            # that are unreliable inside this MyATA custom element.\n            row.evaluate("(el) => el.click()")\n            page.wait_for_timeout(1200)\n            return cells\n\n    raise RuntimeError(\n        f"Year {year} row not found in searched shooter summary"\n    )\n', "open year"),
    ('def _search_and_open(page, ata, name, manual_assist=False):\n    _open_search(page)\n\n    field = _search_input(page)\n', 'def _search_and_open(page, ata, name, manual_assist=False):\n    # Normally the logged-in user contributes one Yearly Summary table.\n    # A searched shooter adds another. Capture the baseline before searching.\n    baseline_count = _yearly_summary_count(page)\n\n    _open_search(page)\n\n    field = _search_input(page)\n', "search baseline"),
    ('    if _wait_for_yearly_summary(page, timeout_ms=7000):\n        return True\n\n    # Search result may be a custom web component requiring keyboard selection.\n    try:\n        field.press("ArrowDown")\n        field.press("Enter")\n        page.wait_for_timeout(1200)\n    except Exception:\n        pass\n\n    if _wait_for_yearly_summary(page, timeout_ms=5000):\n        return True\n\n    if manual_assist:\n', '    if _wait_for_new_yearly_summary(page, baseline_count, timeout_ms=7000):\n        return True\n\n    # Search result may be a custom web component requiring keyboard selection.\n    try:\n        field.press("ArrowDown")\n        field.press("Enter")\n        page.wait_for_timeout(1200)\n    except Exception:\n        pass\n\n    if _wait_for_new_yearly_summary(page, baseline_count, timeout_ms=5000):\n        return True\n\n    if manual_assist:\n', "search waits"),
    ('        if _wait_for_yearly_summary(page, timeout_ms=3000):\n            return True\n', '        if _wait_for_new_yearly_summary(page, baseline_count, timeout_ms=3000):\n            return True\n', "manual wait"),
]

def main():
    if not TARGET.exists():
        raise SystemExit("Run from H:\\MNTrapTeam\\MNTrapTeam")

    text = TARGET.read_text(encoding="utf-8")

    for old, new, label in REPLACEMENTS:
        if old in text:
            text = text.replace(old, new, 1)
        elif new not in text:
            raise RuntimeError(f"Could not find {label} block.")

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
        "MNTrapTeam 3.6.4 applied: searched-shooter table detection fixed."
    )

if __name__ == "__main__":
    main()
