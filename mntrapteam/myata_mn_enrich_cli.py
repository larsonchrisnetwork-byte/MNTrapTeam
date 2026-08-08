from __future__ import annotations

import argparse
import json
from pathlib import Path

from .connectors import SessionStore, _load_playwright
from .database import Database
from .myata_bulk_dom_cli import (
    MYATA_URL,
    _open_year_detail,
    _score_detail_table,
    _search_and_open,
    _table_rows,
)
from .myata_mn_enrichment import (
    SOSClubDirectory,
    enrich_score_detail_rows,
    ensure_status_table,
    save_enrichment,
)
from .paths import DATA


def _settings():
    path = Path("config/settings.json")
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8-sig")
    return json.loads(text) if text.strip() else {}


def _ata(value):
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _candidates(database, season: int, limit: int | None, refresh: bool):
    ensure_status_table(database)

    rows = database.query(
        """
        SELECT DISTINCT
            s.id,
            s.ata_number,
            s.display_name,
            st.mn_singles_targets,
            st.mn_handicap_targets,
            st.mn_doubles_targets,
            st.mn_clubs,
            e.shooter_id AS enriched
        FROM haa_qualifications h
        JOIN shooters s
          ON s.id=h.shooter_id
        JOIN season_stats st
          ON st.shooter_id=s.id
         AND st.season=h.season
        LEFT JOIN myata_mn_enrichment e
          ON e.shooter_id=s.id
         AND e.season=h.season
        WHERE h.season=?
          AND h.verified=1
          AND lower(COALESCE(st.source,'')) LIKE 'myata%'
          AND s.ata_number IS NOT NULL
          AND trim(s.ata_number)<>''
        ORDER BY s.display_name
        """,
        (season,),
    )

    values = []

    for row in rows:
        item = dict(row)
        if not refresh and item.get("enriched") is not None:
            continue
        values.append(item)

    return values[:limit] if limit else values


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Populate Minnesota target and club eligibility from MyATA details"
    )
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--manual-assist", action="store_true")
    args = parser.parse_args()

    database = Database(DATA / "mntrapteam.db")
    directory = SOSClubDirectory.from_latest_capture(DATA)
    shooters = _candidates(database, args.season, args.limit, args.refresh)

    settings = _settings()
    self_ata = _ata(settings.get("user_ata_number"))

    print(f"SOS club directory: {directory.source_path}")
    print(f"Clubs loaded: {len(directory.rows)}")
    print(f"Shooters in this enrichment batch: {len(shooters)}")

    if not shooters:
        print("No shooters need Minnesota enrichment.")
        return 0

    store = SessionStore(DATA)
    profile = store.profile_dir("shootata")
    sync_playwright = _load_playwright()

    successful = 0
    failed = 0
    unknown_total: set[str] = set()

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(profile),
            headless=False,
            viewport={"width": 1500, "height": 1000},
            args=["--start-maximized"],
        )
        page = context.pages[0] if context.pages else context.new_page()

        page.goto(
            MYATA_URL,
            wait_until="domcontentloaded",
            timeout=60000,
        )

        print()
        print("MyATA Minnesota-eligibility enrichment is ready.")
        print("Complete login if necessary.")
        input("When Shooter Information Center is ready, press Enter... ")

        if context.pages:
            page = context.pages[-1]

        for position, shooter in enumerate(shooters, 1):
            ata = _ata(shooter["ata_number"])
            name = str(shooter["display_name"]).strip()

            print()
            print(f"[{position}/{len(shooters)}] {name} | ATA {ata}")

            try:
                if self_ata and ata == self_ata:
                    # The user's row already had working MN eligibility before
                    # the bulk import. Preserve it rather than risk replacing
                    # it with a failed self-navigation scrape.
                    existing = (
                        int(shooter.get("mn_singles_targets") or 0)
                        + int(shooter.get("mn_handicap_targets") or 0)
                        + int(shooter.get("mn_doubles_targets") or 0)
                        + int(shooter.get("mn_clubs") or 0)
                    )

                    if existing > 0:
                        print("  Existing self MN eligibility preserved.")
                        successful += 1
                        continue

                    raise RuntimeError(
                        "Logged-in self record has no existing Minnesota eligibility data"
                    )

                last_error = None
                rows = None

                for attempt in range(1, 3):
                    try:
                        opened = _search_and_open(
                            page,
                            ata,
                            name,
                            manual_assist=(
                                args.manual_assist and attempt == 2
                            ),
                        )

                        if not opened:
                            raise RuntimeError(
                                "Search/Buddies shooter did not open"
                            )

                        _open_year_detail(
                            page,
                            args.season,
                            manual_assist=(
                                args.manual_assist and attempt == 2
                            ),
                        )

                        detail = _score_detail_table(
                            page,
                            args.season,
                        )
                        rows = _table_rows(detail)
                        break

                    except Exception as exc:
                        last_error = exc

                        if attempt == 1:
                            print(f"  Attempt 1 failed: {exc}")
                            print("  Retrying shooter once...")

                            try:
                                page.goto(
                                    MYATA_URL,
                                    wait_until="domcontentloaded",
                                    timeout=60000,
                                )
                                page.wait_for_timeout(800)
                            except Exception:
                                pass

                if rows is None:
                    raise RuntimeError(
                        f"Retry failed: {last_error}"
                    )
                totals = enrich_score_detail_rows(rows, directory)

                print(
                    f"  MN Singles: {totals.singles_targets} | "
                    f"MN Handicap: {totals.handicap_targets} | "
                    f"MN Doubles: {totals.doubles_targets} | "
                    f"MN Clubs: {totals.mn_clubs}"
                )

                if totals.unknown_clubs:
                    print(
                        f"  Unmatched club names: {len(totals.unknown_clubs)}"
                    )
                    for club in totals.unknown_clubs[:8]:
                        print(f"    ? {club}")
                    unknown_total.update(totals.unknown_clubs)

                if args.dry_run:
                    print("  DRY RUN: database unchanged.")
                else:
                    save_enrichment(
                        database,
                        int(shooter["id"]),
                        args.season,
                        totals,
                    )
                    print("  Minnesota eligibility fields updated.")

                successful += 1

            except Exception as exc:
                failed += 1
                print("  FAILED:", exc)

            try:
                page.goto(
                    MYATA_URL,
                    wait_until="domcontentloaded",
                    timeout=60000,
                )
                page.wait_for_timeout(500)
            except Exception:
                pass

        print()
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Unique unmatched club names: {len(unknown_total)}")

        if unknown_total:
            report = DATA / "connector_downloads" / "myata_mn_unknown_clubs.txt"
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text(
                "\n".join(sorted(unknown_total)) + "\n",
                encoding="utf-8",
            )
            print(f"Unknown-club report: {report}")

        input("Press Enter to close the browser... ")
        context.close()

    return 0 if successful else 2


if __name__ == "__main__":
    raise SystemExit(main())
