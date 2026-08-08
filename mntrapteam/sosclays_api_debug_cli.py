from __future__ import annotations

import argparse
import json
from urllib.request import Request, urlopen

BASE = "https://www.sosclays.com"
ENDPOINTS = [
    "/api/active-shoots",
    "/api/clubs",
    "/api/state-shoots",
]


def fetch_json(url: str, timeout: int = 15):
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 MNTrapTeam/5.1.0",
            "Accept": "application/json,text/plain,*/*",
        },
    )
    with urlopen(req, timeout=timeout) as response:
        data = response.read().decode("utf-8", errors="replace")
        return response.status, response.geturl(), data


def summarize(value, depth=0, max_depth=3):
    indent = "  " * depth
    if depth > max_depth:
        print(indent + "...")
        return

    if isinstance(value, dict):
        print(indent + f"dict keys={list(value.keys())[:30]}")
        for k, v in list(value.items())[:12]:
            print(indent + f"{k}:")
            summarize(v, depth + 1, max_depth)
    elif isinstance(value, list):
        print(indent + f"list len={len(value)}")
        for i, item in enumerate(value[:5]):
            print(indent + f"[{i}]")
            summarize(item, depth + 1, max_depth)
    else:
        print(indent + repr(value)[:500])


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only diagnostic for SOS Clays public JSON endpoints."
    )
    parser.add_argument(
        "--endpoint",
        action="append",
        default=[],
        help="Additional endpoint or full URL to inspect.",
    )
    args = parser.parse_args()

    print("MNTrapTeam SOS Clays API Diagnostic")
    print("===================================")
    print("READ ONLY — no database changes.")
    print()

    endpoints = ENDPOINTS + args.endpoint

    for raw in endpoints:
        url = raw if raw.startswith("http") else BASE + raw
        print(url)
        print("-" * len(url))

        try:
            status, final_url, text = fetch_json(url)
        except Exception as exc:
            print(f"FAILED: {type(exc).__name__}: {exc}")
            print()
            continue

        print(f"status: {status}")
        print(f"final URL: {final_url}")
        print(f"bytes: {len(text.encode('utf-8'))}")

        try:
            data = json.loads(text)
        except Exception:
            print("Not valid JSON.")
            print(text[:3000])
            print()
            continue

        summarize(data)

        print()
        print("FIRST JSON SAMPLE")
        print("-----------------")
        try:
            if isinstance(data, list):
                sample = data[:3]
            elif isinstance(data, dict):
                sample = data
            else:
                sample = data
            print(json.dumps(sample, indent=2)[:12000])
        except Exception:
            print(repr(data)[:12000])

        print()
        print("=" * 72)
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
