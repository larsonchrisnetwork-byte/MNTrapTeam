from __future__ import annotations

from pathlib import Path
import argparse
import csv
import re

from .connectors import SessionStore, _load_playwright
from .database import Database
from .myata_dom_parser import (
    parse_score_detail_rows,
    parse_year_summary_row,
    validate_detail_against_summary,
)
from .paths import DATA
from .official_baseline import official_through_date_from_detail_rows, save_baseline


MYATA_URL = "https://shootata.com/Shooter-Information-Center"


def _visible(locator):
    try:
        return locator.count() > 0 and locator.first.is_visible()
    except Exception:
        return False


def _yearly_summary_count(page):
    count = 0
    tables = page.locator("table")
    for index in range(tables.count()):
        table = tables.nth(index)
        try:
            if "Shooter Yearly Summary" in table.inner_text(timeout=300):
                count += 1
        except Exception:
            pass
    return count


def _wait_for_new_yearly_summary(page, baseline_count, timeout_ms=15000):
    """Wait until Search/Buddies adds another Yearly Summary table."""
    import time
    deadline = time.monotonic() + (timeout_ms / 1000.0)
    while time.monotonic() < deadline:
        if _yearly_summary_count(page) > baseline_count:
            return True
        page.wait_for_timeout(250)
    return False


def _yearly_tables(page):
    result = []
    tables = page.locator("table")
    for index in range(tables.count()):
        table = tables.nth(index)
        try:
            table_text = table.inner_text(timeout=800)
        except Exception:
            continue
        if "Shooter Yearly Summary" in table_text:
            result.append(table)
    return result


def _searched_yearly_table(page):
    tables = _yearly_tables(page)
    if not tables:
        raise RuntimeError("No Shooter Yearly Summary table is available")

    # _search_and_open() already verifies that the number of summary tables
    # increased over the pre-search baseline. Depending on MyATA page state,
    # that can mean 0 -> 1 or 1 -> 2. In either case, the last summary table
    # is the newly opened searched shooter.
    return tables[-1]


def _score_detail_table(page, year):
    target = f"{year} Score Details"
    tables = page.locator("table")
    result = []
    for index in range(tables.count()):
        table = tables.nth(index)
        try:
            if target in table.inner_text(timeout=800):
                result.append(table)
        except Exception:
            pass
    if not result:
        raise RuntimeError(f"No {target} table is available")
    return result[-1]


def _table_rows(table):
    result = []
    rows = table.locator("tr")
    for index in range(rows.count()):
        cells = rows.nth(index).locator("th,td").all_inner_texts()
        result.append([" ".join(str(cell).split()) for cell in cells])
    return result


def _open_search(page):
    choices = [
        page.get_by_text("Search/Buddies", exact=True),
        page.get_by_role("button", name=re.compile("Search/Buddies", re.I)),
        page.locator('button:has-text("Search/Buddies")'),
    ]
    for choice in choices:
        try:
            if choice.count() and choice.first.is_visible():
                choice.first.click()
                page.wait_for_timeout(600)
                return
        except Exception:
            pass


def _search_input(page):
    candidates = page.locator(
        'input[type="search"],'
        'input[placeholder*="ATA" i],'
        'input[placeholder*="search" i],'
        'input[name*="search" i],'
        'input[id*="search" i]'
    )

    for index in range(candidates.count()):
        item = candidates.nth(index)
        try:
            if item.is_visible():
                return item
        except Exception:
            pass

    generic = page.locator(
        'input:not([type="hidden"]):not([type="password"]):'
        'not([type="submit"]):not([type="button"])'
    )
    visible = []
    for index in range(generic.count()):
        item = generic.nth(index)
        try:
            if item.is_visible():
                visible.append(item)
        except Exception:
            pass

    if not visible:
        raise RuntimeError("Could not find Search/Buddies input")

    return visible[-1]


def _click_search_result(page, ata, name):
    # Search the whole rendered DOM for clickable ancestors containing
    # ATA number or exact shooter name.
    result = page.evaluate(
        """({ata, name}) => {
            const norm = s => (s || '').replace(/\\s+/g, ' ').trim().toLowerCase();
            const targets = [ata.toLowerCase(), name.toLowerCase()];

            const all = Array.from(document.querySelectorAll('*'));
            const matches = all.filter(el => {
                const txt = norm(el.innerText);
                if (!txt) return false;
                return targets.some(t => txt === t || txt.includes(t));
            });

            for (const el of matches) {
                let cur = el;
                for (let i = 0; i < 6 && cur; i++, cur = cur.parentElement) {
                    const tag = (cur.tagName || '').toLowerCase();
                    const role = (cur.getAttribute && cur.getAttribute('role')) || '';
                    const clickable =
                        tag === 'button' || tag === 'a' ||
                        role === 'button' || role === 'option' ||
                        role === 'row' || role === 'listitem' ||
                        typeof cur.onclick === 'function' ||
                        (cur.getAttribute && cur.getAttribute('tabindex') !== null);

                    if (clickable) {
                        cur.click();
                        return {
                            clicked: true,
                            tag,
                            role,
                            text: norm(cur.innerText).slice(0, 300)
                        };
                    }
                }
            }

            return {clicked: false, matches: matches.length};
        }""",
        {"ata": ata, "name": name},
    )
    page.wait_for_timeout(1200)
    return result


def _ranked_search_fields(page):
    """Return Search/Buddies inputs with the ATA-number field first."""
    candidates = page.locator("ata-shooter-information-center input")

    if candidates.count() == 0:
        candidates = page.locator("input")

    ranked = []

    for index in range(candidates.count()):
        field = candidates.nth(index)

        try:
            if not field.is_visible() or field.is_disabled():
                continue
        except Exception:
            continue

        try:
            metadata = field.evaluate(
                """(el) => {
                    const parts = [
                        el.getAttribute('name') || '',
                        el.getAttribute('id') || '',
                        el.getAttribute('placeholder') || '',
                        el.getAttribute('aria-label') || '',
                        el.getAttribute('title') || ''
                    ];

                    if (el.labels) {
                        for (const label of el.labels) {
                            parts.push(label.innerText || '');
                        }
                    }

                    let node = el.parentElement;
                    for (let i = 0; i < 3 && node; i++, node = node.parentElement) {
                        parts.push(node.innerText || '');
                    }

                    return parts.join(' ').replace(/\\s+/g, ' ').trim();
                }"""
            )
        except Exception:
            metadata = ""

        upper = str(metadata or "").upper()

        score = 0

        if "ATA NUMBER" in upper:
            score += 100
        elif "ATA #" in upper or "ATA#" in upper:
            score += 95
        elif "ATA" in upper:
            score += 80

        if "LAST NAME" in upper:
            score -= 30

        if "FIRST NAME" in upper:
            score -= 30

        ranked.append((score, index, field, metadata))

    ranked.sort(
        key=lambda item: (
            -item[0],
            item[1],
        )
    )

    return ranked


def _load_settings():
    import json
    path = Path("config/settings.json")
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8-sig")
    return json.loads(text) if text.strip() else {}


def _normalized_ata(value):
    return "".join(
        character for character in str(value or "")
        if character.isdigit()
    )


def _self_ata_number():
    settings = _load_settings()
    return _normalized_ata(settings.get("user_ata_number"))


def _self_yearly_table(page):
    tables = _yearly_tables(page)
    if not tables:
        raise RuntimeError("Logged-in MyATA Yearly Summary is not available")
    return tables[0]


def _open_self_year_detail(page, year, manual_assist=False):
    table = _self_yearly_table(page)
    rows = table.locator("tr")

    for index in range(rows.count()):
        row = rows.nth(index)
        cells = [
            " ".join(x.split())
            for x in row.locator("th,td").all_inner_texts()
        ]
        if not cells or cells[0] != str(year):
            continue

        cell = row.locator("th,td").first
        try:
            cell.click(timeout=5000, force=True)
        except Exception:
            try:
                cell.evaluate("(el) => el.click()")
            except Exception:
                row.evaluate("(el) => el.click()")

        page.wait_for_timeout(1000)
        try:
            detail = _score_detail_table(page, year)
            return cells, detail
        except Exception:
            pass

        if manual_assist:
            print()
            print(f"  Automatic My Scores {year} detail-open failed.")
            print(f"  In the browser, click your {year} row so that")
            print(f"  {year} Score Details is visible.")
            input("  Then return here and press Enter... ")
            detail = _score_detail_table(page, year)
            return cells, detail

        raise RuntimeError(
            f"Logged-in {year} summary found, but Score Details did not open"
        )

    raise RuntimeError(f"Year {year} not found in logged-in MyATA summary")


def _scrape_self(page, year, manual_assist=False):
    summary_cells, detail = _open_self_year_detail(
        page,
        year,
        manual_assist=manual_assist,
    )
    summary = parse_year_summary_row(summary_cells)
    detail_rows = _table_rows(detail)
    totals = parse_score_detail_rows(detail_rows)
    warnings = validate_detail_against_summary(totals, summary)
    through_date = official_through_date_from_detail_rows(detail_rows)
    return totals, warnings, through_date


def _find_result_button(page, name):
    parts = [part for part in re.split(r"\s+", str(name).strip()) if part]
    first = parts[0].upper() if parts else ""
    last = parts[-1].upper() if parts else ""

    buttons = page.locator("ata-shooter-information-center button")
    if buttons.count() == 0:
        buttons = page.locator("button")

    shooter_results = []

    for index in range(buttons.count()):
        button = buttons.nth(index)
        try:
            text = " ".join(button.inner_text(timeout=500).split()).upper()
        except Exception:
            continue

        if not text:
            continue

        # Exclude the fixed Shooter Information Center navigation controls.
        if text in {
            "MY SCORES",
            "SEARCH/BUDDIES",
            "QUICK LIST",
            "ALL AMERICAN",
        }:
            continue

        # Search/Buddies shooter results are rendered like:
        # WEBER, AIDEN KENITH. - MONTICELLO, MN
        # Require the result-like comma + location separator pattern so an
        # unrelated page button is not mistaken for a shooter.
        if "," in text and " - " in text:
            shooter_results.append((button, text))

    # Exact ATA-number searches normally return one shooter. Trust that unique
    # result even if our database uses a nickname (Eli) and ATA shows the
    # formal first name (Elias).
    if len(shooter_results) == 1:
        return shooter_results[0][0]

    # If more than one result is present, fall back to name matching.
    for button, text in shooter_results:
        if first and last and first in text and last in text:
            return button

    # Last-name-only fallback is safe only when it identifies a single result.
    if last:
        last_matches = [
            button
            for button, text in shooter_results
            if last in text
        ]
        if len(last_matches) == 1:
            return last_matches[0]

    return None


def _search_and_open(page, ata, name, manual_assist=False):
    baseline_count = _yearly_summary_count(page)

    _open_search(page)
    page.wait_for_timeout(600)

    # Search/Buddies is a custom web component. Rather than assuming one
    # particular input, try each usable input inside the ATA component and
    # accept only the input that produces the expected shooter result button.
    ranked_fields = _ranked_search_fields(page)

    for _score, _index, field, _metadata in ranked_fields:
        try:
            field.click(timeout=1500)
            field.fill("")
            field.fill(ata)
            page.wait_for_timeout(900)

            result = _find_result_button(page, name)

            if result is None:
                try:
                    field.press("Enter")
                    page.wait_for_timeout(700)
                except Exception:
                    pass
                result = _find_result_button(page, name)

            if result is None:
                try:
                    field.fill("")
                except Exception:
                    pass
                continue

            try:
                result.click(timeout=5000)
            except Exception:
                result.evaluate("(el) => el.click()")

            page.wait_for_timeout(1000)

            if _wait_for_new_yearly_summary(
                page,
                baseline_count,
                timeout_ms=7000,
            ):
                return True

        except Exception:
            continue

    if manual_assist:
        print()
        print(f"  Automatic ATA search failed for {name}.")
        print("  The browser will remain open.")
        print(f"  In Search/Buddies, manually search ATA {ata}.")
        print(f"  Click the result for {name}.")
        print("  Leave that shooter's Yearly Summary visible.")
        input("  Then return here and press Enter... ")

        if _wait_for_new_yearly_summary(
            page,
            baseline_count,
            timeout_ms=3000,
        ):
            return True

    return False


def _open_year_detail(page, year, manual_assist=False):
    table = _searched_yearly_table(page)
    rows = table.locator("tr")

    for index in range(rows.count()):
        row = rows.nth(index)
        cells = [
            " ".join(x.split())
            for x in row.locator("th,td").all_inner_texts()
        ]

        if not cells or cells[0] != str(year):
            continue

        year_cell = row.locator("th,td").first

        try:
            year_cell.click(timeout=5000, force=True)
        except Exception:
            try:
                year_cell.evaluate("(el) => el.click()")
            except Exception:
                row.evaluate("(el) => el.click()")

        page.wait_for_timeout(1000)

        try:
            _score_detail_table(page, year)
            return cells
        except Exception:
            pass

        if manual_assist:
            print()
            print(f"  Automatic {year} detail-open failed.")
            print(f"  In the browser, click {year} so that")
            print(f"  {year} Score Details is visible.")
            input("  Then return here and press Enter... ")

            try:
                _score_detail_table(page, year)
                return cells
            except Exception:
                pass

        raise RuntimeError(
            f"{year} summary found, but {year} Score Details did not open"
        )

    raise RuntimeError(
        f"Year {year} row not found in searched shooter summary"
    )


def _scrape(page, year, manual_assist=False):
    summary_cells = _open_year_detail(
        page,
        year,
        manual_assist=manual_assist,
    )
    summary = parse_year_summary_row(summary_cells)

    detail = _score_detail_table(page, year)
    detail_rows = _table_rows(detail)
    totals = parse_score_detail_rows(detail_rows)
    warnings = validate_detail_against_summary(totals, summary)
    through_date = official_through_date_from_detail_rows(detail_rows)
    return totals, warnings, through_date


def _candidates(db, season, limit, *, refresh=False, ata_file=''):
    rows = db.query(
        """
        SELECT DISTINCT
            s.id,
            s.ata_number,
            s.display_name,
            COALESCE(st.source, '') AS existing_source
        FROM shooters s
        LEFT JOIN season_stats st
          ON st.shooter_id=s.id
         AND st.season=?
        WHERE s.ata_number IS NOT NULL
          AND trim(s.ata_number)<>''
          AND (
              EXISTS(
                  SELECT 1
                  FROM haa_qualifications h
                  WHERE h.shooter_id=s.id
                    AND h.season=?
                    AND h.verified=1
              )
              OR EXISTS(
                  SELECT 1
                  FROM zone_haa_qualifications z
                  WHERE z.shooter_id=s.id
                    AND z.season=?
                    AND z.verified=1
              )
          )
        ORDER BY s.display_name
        """,
        (season, season, season),
    )

    targeted = None
    targeted_order = {}
    if ata_file:
        with open(ata_file, "r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if "ata_number" not in (reader.fieldnames or []):
                raise ValueError("ATA file must contain an ata_number column")
            ordered = [
                "".join(ch for ch in str(item.get("ata_number") or "") if ch.isdigit())
                for item in reader
                if str(item.get("ata_number") or "").strip()
            ]
        targeted = set(ordered)
        targeted_order = {ata: index for index, ata in enumerate(ordered)}

    values = []
    for row in rows:
        item = dict(row)
        normalized_ata = "".join(
            ch for ch in str(item.get("ata_number") or "") if ch.isdigit()
        )
        if targeted is not None and normalized_ata not in targeted:
            continue

        source = str(item.get("existing_source") or "").strip().lower()

        if targeted is None and not refresh and source.startswith("myata"):
            # Any existing MyATA baseline is already an official ATA source.
            # This includes the logged-in user, whose earlier MyATA capture
            # may use a different source label than the rendered bulk scraper.
            continue
        values.append(item)

    if targeted is not None:
        values.sort(
            key=lambda item: targeted_order.get(
                "".join(
                    ch for ch in str(item.get("ata_number") or "") if ch.isdigit()
                ),
                999999,
            )
        )
        return values
    return values[:limit] if limit else values


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument(
        "--ata-file",
        default="",
        help="CSV containing ata_number and optional display_name; process only those shooters",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Re-import shooters with an existing rendered MyATA baseline",
    )
    parser.add_argument(
        "--manual-assist",
        action="store_true",
        help="Pause for manual result selection if MyATA custom UI defeats automation",
    )
    args = parser.parse_args()

    db = Database(DATA / "mntrapteam.db")
    shooters = _candidates(
        db,
        args.season,
        args.limit,
        refresh=args.refresh,
        ata_file=args.ata_file,
    )

    store = SessionStore(DATA)
    profile = store.profile_dir("shootata")
    sync_playwright = _load_playwright()

    success = 0
    failed = 0

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(profile),
            headless=False,
            viewport={"width": 1500, "height": 1000},
            args=["--start-maximized"],
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(MYATA_URL, wait_until="domcontentloaded", timeout=60000)

        print()
        print("MyATA bulk baseline test is ready.")
        print("Complete login if needed and leave Shooter Information Center open.")
        input("When ready, press Enter... ")

        if context.pages:
            page = context.pages[-1]

        for pos, shooter in enumerate(shooters, 1):
            ata = str(shooter["ata_number"]).strip()
            name = str(shooter["display_name"]).strip()

            print()
            print(f"[{pos}/{len(shooters)}] {name} | ATA {ata}")

            try:
                self_ata = _self_ata_number()

                if self_ata and _normalized_ata(ata) == self_ata:
                    print("  Using logged-in My Scores record.")
                    try:
                        totals, warnings, through_date = _scrape_self(
                            page,
                            args.season,
                            manual_assist=args.manual_assist,
                        )
                    except Exception as self_exc:
                        print(
                            "  Logged-in My Scores path failed; "
                            "falling back to Search/Buddies."
                        )
                        print(f"  My Scores reason: {self_exc}")
                        opened = _search_and_open(
                            page,
                            ata,
                            name,
                            manual_assist=args.manual_assist,
                        )
                        if not opened:
                            raise RuntimeError(
                                "Self fallback Search/Buddies result was not opened"
                            ) from self_exc
                        totals, warnings, through_date = _scrape(
                            page,
                            args.season,
                            manual_assist=args.manual_assist,
                        )
                else:
                    opened = _search_and_open(
                        page,
                        ata,
                        name,
                        manual_assist=args.manual_assist,
                    )
                    if not opened:
                        raise RuntimeError(
                            "Search result was not opened; no new Yearly Summary appeared"
                        )

                    totals, warnings, through_date = _scrape(
                        page,
                        args.season,
                        manual_assist=args.manual_assist,
                    )

                print(
                    f"  Singles: {totals.singles_targets} / {totals.singles_hits} "
                    f"({totals.singles_average:.2f}%)"
                )
                print(
                    f"  Handicap: {totals.handicap_targets} / {totals.handicap_hits} "
                    f"({totals.handicap_average:.2f}%)"
                )
                print(
                    f"  Doubles: {totals.doubles_targets} / {totals.doubles_hits} "
                    f"({totals.doubles_average:.2f}%)"
                )

                if warnings:
                    for warning in warnings:
                        print("  WARNING:", warning)
                    raise RuntimeError("Detail totals did not match summary")

                if args.dry_run:
                    print("  DRY RUN: database unchanged.")
                else:
                    db.upsert_stats(
                        int(shooter["id"]),
                        args.season,
                        singles_targets=totals.singles_targets,
                        singles_hits=totals.singles_hits,
                        handicap_targets=totals.handicap_targets,
                        handicap_hits=totals.handicap_hits,
                        doubles_targets=totals.doubles_targets,
                        doubles_hits=totals.doubles_hits,
                        source="MyATA official rendered detail",
                        official=1,
                    )
                    save_baseline(
                        db,
                        int(shooter["id"]),
                        args.season,
                        totals,
                        through_date,
                    )
                    print(
                        "  Official baseline imported."
                        + (
                            f" Official through {through_date}."
                            if through_date
                            else " Official-through date unavailable."
                        )
                    )

                success += 1

            except Exception as exc:
                failed += 1
                print("  FAILED:", exc)

            # Re-open main page between shooters so each search starts clean.
            try:
                page.goto(MYATA_URL, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(500)
            except Exception:
                pass

        print()
        print(f"Successful: {success}")
        print(f"Failed: {failed}")
        input("Press Enter to close the browser... ")
        context.close()

    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())
