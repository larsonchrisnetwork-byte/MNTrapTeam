from pathlib import Path
import re

VERSION = "3.6.3"
TARGET = Path("mntrapteam/myata_bulk_dom_cli.py")

OLD_YEARLY = 'def _yearly_tables(page):\n    result = []\n    tables = page.locator("table")\n    for index in range(tables.count()):\n        table = tables.nth(index)\n        try:\n            text = table.inner_text(timeout=800)\n        except Exception:\n            continue\n        if "Shooter Yearly Summary" in text:\n            result.append(table)\n    return result\n'
NEW_YEARLY = 'def _yearly_tables(page):\n    result = []\n    tables = page.locator("table")\n    for index in range(tables.count()):\n        table = tables.nth(index)\n        try:\n            if not table.is_visible():\n                continue\n            table_text = table.inner_text(timeout=800)\n        except Exception:\n            continue\n        if "Shooter Yearly Summary" in table_text:\n            result.append(table)\n    return result\n'
OLD_DETAIL = 'def _score_detail_table(page, year):\n    target = f"{year} Score Details"\n    tables = page.locator("table")\n    result = []\n    for index in range(tables.count()):\n        table = tables.nth(index)\n        try:\n            if target in table.inner_text(timeout=800):\n                result.append(table)\n        except Exception:\n            pass\n    if not result:\n        raise RuntimeError(f"No {target} table is visible")\n    return result[-1]\n'
NEW_DETAIL = 'def _score_detail_table(page, year):\n    target = f"{year} Score Details"\n    tables = page.locator("table")\n    result = []\n    for index in range(tables.count()):\n        table = tables.nth(index)\n        try:\n            if not table.is_visible():\n                continue\n            if target in table.inner_text(timeout=800):\n                result.append(table)\n        except Exception:\n            pass\n    if not result:\n        raise RuntimeError(f"No visible {target} table is available")\n    return result[-1]\n'
OLD_OPEN = 'def _open_year_detail(page, year):\n    table = _searched_yearly_table(page)\n    rows = table.locator("tr")\n\n    for index in range(rows.count()):\n        row = rows.nth(index)\n        cells = [" ".join(x.split()) for x in row.locator("th,td").all_inner_texts()]\n        if cells and cells[0] == str(year):\n            row.click()\n            page.wait_for_timeout(900)\n            return cells\n\n    raise RuntimeError(f"Year {year} not found in searched shooter table")\n'
NEW_OPEN = 'def _open_year_detail(page, year):\n    table = _searched_yearly_table(page)\n    rows = table.locator("tr")\n\n    for index in range(rows.count()):\n        row = rows.nth(index)\n        try:\n            if not row.is_visible():\n                continue\n        except Exception:\n            continue\n\n        cells = [\n            " ".join(x.split())\n            for x in row.locator("th,td").all_inner_texts()\n        ]\n\n        if cells and cells[0] == str(year):\n            try:\n                row.click(timeout=5000)\n            except Exception:\n                row.evaluate("(el) => el.click()")\n            page.wait_for_timeout(1200)\n            return cells\n\n    raise RuntimeError(\n        f"Visible year {year} row not found in searched shooter table"\n    )\n'
OLD_SEARCH = 'def _searched_yearly_table(page):\n    tables = _yearly_tables(page)\n    if not tables:\n        raise RuntimeError("No Shooter Yearly Summary table is visible")\n    return tables[-1]\n'
NEW_SEARCH = 'def _searched_yearly_table(page):\n    tables = _yearly_tables(page)\n    if not tables:\n        raise RuntimeError("No visible Shooter Yearly Summary table is available")\n    return tables[-1]\n'

def replace_once(text, old, new, label):
    if old in text:
        return text.replace(old, new, 1)
    if new in text:
        return text
    raise RuntimeError(f"Could not find {label} block.")

def main():
    if not TARGET.exists():
        raise SystemExit("Run from H:\\MNTrapTeam\\MNTrapTeam")

    text = TARGET.read_text(encoding="utf-8")
    text = replace_once(text, OLD_YEARLY, NEW_YEARLY, "_yearly_tables")
    text = replace_once(text, OLD_DETAIL, NEW_DETAIL, "_score_detail_table")
    text = replace_once(text, OLD_OPEN, NEW_OPEN, "_open_year_detail")
    text = replace_once(text, OLD_SEARCH, NEW_SEARCH, "_searched_yearly_table")

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

    print("MNTrapTeam 3.6.3 applied: visible MyATA table/row selection fixed.")

if __name__ == "__main__":
    main()
