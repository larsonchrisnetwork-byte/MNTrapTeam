from __future__ import annotations

import argparse
from pathlib import Path

from bs4 import BeautifulSoup

from .connectors import _load_playwright


BASE = "https://scores.shootata.com/shoot/{shoot_id}/{event_id}"


def table_rows(html: str) -> list[list[str]]:
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    if not tables:
        return []

    rows = []
    for tr in tables[0].find_all("tr"):
        cells = [
            " ".join(cell.stripped_strings).strip()
            for cell in tr.find_all(["th", "td"])
        ]
        if cells:
            rows.append(cells)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read all Grand aggregate pages using browser pagination."
    )
    parser.add_argument("--shoot-id", type=int, default=1331)
    args = parser.parse_args()

    sync_playwright = _load_playwright()

    print("MNTrapTeam Grand Browser Pagination Diagnostic")
    print("==============================================")
    print("READ ONLY — no database changes.")
    print()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1500, "height": 1000})

        for event_id, label in ((888, "Prelim Week Scores"), (999, "Grand Week Scores")):
            url = BASE.format(shoot_id=args.shoot_id, event_id=event_id)
            print(f"{label}")
            print("-" * len(label))
            print(url)

            page.goto(url, wait_until="networkidle", timeout=60000)

            seen_ata = set()
            collected = []

            page_num = 1
            while True:
                rows = table_rows(page.content())
                data_rows = rows[1:] if rows else []

                added = 0
                for row in data_rows:
                    if len(row) < 2:
                        continue
                    ata = row[1].strip()
                    if not ata or not ata.isdigit():
                        continue
                    if ata in seen_ata:
                        continue
                    seen_ata.add(ata)
                    collected.append(row)
                    added += 1

                print(
                    f"  page {page_num}: rows={len(data_rows)} "
                    f"new={added} total={len(collected)}",
                    flush=True,
                )

                next_button = page.get_by_role("button", name="Next", exact=True)
                if next_button.count() == 0:
                    break

                try:
                    disabled = next_button.is_disabled()
                except Exception:
                    disabled = False

                if disabled:
                    break

                before = page.locator("table").inner_text()
                next_button.click()
                page.wait_for_timeout(400)

                try:
                    page.wait_for_function(
                        """before => {
                            const t = document.querySelector('table');
                            return t && t.innerText !== before;
                        }""",
                        arg=before,
                        timeout=3000,
                    )
                except Exception:
                    pass

                after = page.locator("table").inner_text()
                if after == before:
                    break

                page_num += 1
                if page_num > 200:
                    raise RuntimeError("Pagination safety limit reached")

            print(f"  TOTAL UNIQUE SHOOTERS: {len(collected)}")
            print()

            # Show just frozen-pool-relevant ATA rows if a target CSV exists later;
            # for now save complete CSV-like TSV for inspection.
            out = Path("data") / "connector_downloads" / f"grand_{event_id}_all_rows.tsv"
            out.parent.mkdir(parents=True, exist_ok=True)
            with out.open("w", encoding="utf-8-sig") as handle:
                for row in collected:
                    handle.write("\t".join(row) + "\n")
            print(f"  Saved: {out}")
            print()

        browser.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
