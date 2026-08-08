from __future__ import annotations

import argparse
import re
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

BASE = "https://scores.shootata.com/shoot/{shoot_id}/{event_id}"


def fetch(url: str, timeout: int = 10) -> str:
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 MNTrapTeam/4.8.2",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def inspect(event_id: int, shoot_id: int) -> None:
    url = BASE.format(shoot_id=shoot_id, event_id=event_id)
    print(f"Event {event_id}: {url}")
    html = fetch(url)
    soup = BeautifulSoup(html, "html.parser")

    tables = soup.find_all("table")
    if tables:
        rows = tables[0].find_all("tr")
        print(f"First table rows on page: {len(rows)}")

    print()
    print("PAGINATION-LIKE LINKS")
    print("---------------------")
    seen = set()
    for a in soup.find_all("a", href=True):
        text = " ".join(a.stripped_strings).strip()
        href = urljoin(url, a["href"])
        blob = f"{text} {href}".lower()
        if any(k in blob for k in ("page", "next", "prev", "offset", "start", "skip", "take")):
            key = (text, href)
            if key not in seen:
                seen.add(key)
                print(f"{text!r} -> {href}")

    print()
    print("BUTTONS")
    print("-------")
    for b in soup.find_all(["button","input"]):
        text = " ".join(b.stripped_strings).strip()
        print(
            f"{b.name} text={text!r} type={b.get('type')!r} "
            f"name={b.get('name')!r} value={b.get('value')!r} "
            f"onclick={b.get('onclick')!r}"
        )

    print()
    print("SCRIPTS WITH PAGINATION HINTS")
    print("-----------------------------")
    for s in soup.find_all("script"):
        content = s.string or s.get_text(" ", strip=True)
        if not content:
            continue
        if re.search(r"page|next|prev|offset|start|skip|take|DataTable", content, re.I):
            snippet = re.sub(r"\s+", " ", content)
            print(snippet[:1500])

    print()
    print("=" * 70)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shoot-id", type=int, default=1331)
    args = parser.parse_args()

    print("MNTrapTeam Grand Pagination Diagnostic")
    print("======================================")
    print("READ ONLY — no database changes.")
    print()

    inspect(888, args.shoot_id)
    inspect(999, args.shoot_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
