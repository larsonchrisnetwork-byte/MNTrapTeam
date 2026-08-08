from __future__ import annotations

import argparse
import re
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

BASE = "https://scores.shootata.com/shoot/{shoot_id}/{event_id}"
DEFAULT_SHOOT_ID = 1331


def fetch(url: str, timeout: int = 10) -> str:
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 MNTrapTeam/4.8.1",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def _table_preview(html: str) -> None:
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    print(f"Tables found: {len(tables)}")

    for ti, table in enumerate(tables, 1):
        rows = table.find_all("tr")
        if not rows:
            continue

        print()
        print(f"TABLE {ti} | rows={len(rows)}")
        for ri, tr in enumerate(rows[:12], 1):
            cells = [
                " ".join(cell.stripped_strings).strip()
                for cell in tr.find_all(["th", "td"])
            ]
            print(f"  row {ri}: {cells}")


def _candidateish_lines(html: str) -> None:
    soup = BeautifulSoup(html, "html.parser")
    lines = []
    for tr in soup.find_all("tr"):
        cells = [
            " ".join(cell.stripped_strings).strip()
            for cell in tr.find_all(["th", "td"])
        ]
        joined = " | ".join(cells)
        if re.search(r"\bMN\b|MINNESOTA", joined, re.I):
            lines.append(joined)

    print()
    print(f"Rows containing MN/MINNESOTA: {len(lines)}")
    for line in lines[:40]:
        print(f"  {line}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect Grand Prelim/Grand Week aggregate pages."
    )
    parser.add_argument("--shoot-id", type=int, default=DEFAULT_SHOOT_ID)
    args = parser.parse_args()

    print("MNTrapTeam Grand Aggregate Diagnostic")
    print("=====================================")
    print("READ ONLY — no database changes.")
    print()

    for event_id, label in ((888, "Prelim Week Scores"), (999, "Grand Week Scores")):
        url = BASE.format(shoot_id=args.shoot_id, event_id=event_id)
        print(f"{label}")
        print("-" * len(label))
        print(f"URL: {url}")
        html = fetch(url)
        soup = BeautifulSoup(html, "html.parser")

        title = " ".join(soup.stripped_strings)
        print(f"Page text start: {title[:220]}")
        _table_preview(html)
        _candidateish_lines(html)

        print()
        print("=" * 70)
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
