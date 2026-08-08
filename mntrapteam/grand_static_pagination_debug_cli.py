from __future__ import annotations

import argparse
import re
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup


def fetch(url: str, timeout: int = 10) -> str:
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 MNTrapTeam/4.8.4",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def inspect(url: str) -> None:
    html = fetch(url)
    soup = BeautifulSoup(html, "html.parser")

    print(f"URL: {url}")
    print(f"HTML bytes: {len(html.encode('utf-8'))}")
    print()

    next_button = None
    for b in soup.find_all("button"):
        text = " ".join(b.stripped_strings).strip()
        if text == "Next":
            next_button = b
            break

    print("NEXT BUTTON OUTER HTML")
    print("----------------------")
    if next_button:
        print(str(next_button))
        print()
        print("NEXT BUTTON PARENT")
        print("------------------")
        print(str(next_button.parent)[:5000])
    else:
        print("Next button not found")

    print()
    print("SCRIPT SOURCES")
    print("--------------")
    for s in soup.find_all("script", src=True):
        print(s.get("src"))

    print()
    print("HTML LINES WITH PAGINATION/API HINTS")
    print("------------------------------------")
    hints = (
        "next", "page", "pagesize", "pageindex", "skip", "take",
        "offset", "api/", "fetch(", "axios", "datatable", "pagination"
    )
    for line in html.splitlines():
        lower = line.lower()
        if any(h in lower for h in hints):
            compact = re.sub(r"\s+", " ", line).strip()
            if compact:
                print(compact[:3000])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shoot-id", type=int, default=1331)
    args = parser.parse_args()

    print("MNTrapTeam Grand Static HTML Pagination Diagnostic")
    print("==================================================")
    print("READ ONLY — no database changes.")
    print()

    for event_id in (888, 999):
        print(f"EVENT {event_id}")
        print("=" * 40)
        inspect(f"https://scores.shootata.com/shoot/{args.shoot_id}/{event_id}")
        print()
        print("#" * 75)
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
