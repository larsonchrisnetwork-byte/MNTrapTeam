from __future__ import annotations

import json
from pathlib import Path
import re

from .paths import DATA


def _latest():
    root = DATA / "connector_downloads" / "scoreboard_zone"
    if not root.exists():
        raise FileNotFoundError("No scoreboard_zone captures found")

    dirs = sorted(
        [
            p for p in root.iterdir()
            if p.is_dir() and p.name.startswith("central_beaverbrook_")
        ],
        key=lambda p: p.stat().st_mtime,
    )

    if not dirs:
        raise FileNotFoundError("No Central Beaverbrook capture found")

    return dirs[-1]


def main() -> int:
    capture = _latest()

    print("MNTrapTeam Central Zone Capture Inspector")
    print("========================================")
    print(f"Capture: {capture}")
    print()

    meta_path = capture / "page_meta.json"
    body_path = capture / "body.txt"

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    body = body_path.read_text(encoding="utf-8")

    print(f"URL: {meta.get('url')}")
    print(f"Title: {meta.get('title')}")
    print()

    print("CENTRAL / BEAVERBROOK / HAA TEXT HITS")
    print("-------------------------------------")

    lines = re.split(r"(?<=[.!?])\s+|\s{2,}", body)

    hits = []
    for line in lines:
        upper = line.upper()
        if any(
            token in upper
            for token in (
                "CENTRAL",
                "BEAVERBROOK",
                "HAA",
                "SINGLES",
                "HANDICAP",
                "DOUBLES",
            )
        ):
            cleaned = " ".join(line.split())
            if cleaned and cleaned not in hits:
                hits.append(cleaned)

    for line in hits[:100]:
        print(line)

    print()
    print("LINKS WITH REPORT/SCORE TERMS")
    print("-----------------------------")

    count = 0
    for link in meta.get("links") or []:
        text = str(link.get("text") or "")
        href = str(link.get("href") or "")
        hay = f"{text} {href}".upper()

        if any(
            token in hay
            for token in (
                "RESULT",
                "REPORT",
                "HIGH",
                "HAA",
                "SCORE",
                "SHOOTID",
            )
        ):
            print(f"{text!r} -> {href}")
            count += 1

    print()
    print(f"Report-like links: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
