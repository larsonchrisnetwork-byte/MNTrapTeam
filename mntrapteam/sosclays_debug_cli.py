from __future__ import annotations

import argparse
import re
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from bs4 import BeautifulSoup


CANDIDATES = [
    "https://www.sosclays.com/",
    "https://www.sosclays.com/scores",
    "https://www.sosclays.com/results",
    "https://www.sosclays.com/shoots",
    "https://www.sosclays.com/events",
]


def fetch(url: str, timeout: int = 12):
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 MNTrapTeam/4.9.0",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urlopen(req, timeout=timeout) as response:
        return (
            response.geturl(),
            response.status,
            response.read().decode("utf-8", errors="replace"),
        )


def inspect(label: str, url: str) -> None:
    print(f"{label}: {url}")
    try:
        final_url, status, html = fetch(url)
    except HTTPError as exc:
        print(f"  HTTP {exc.code}: {exc.reason}")
        print()
        return
    except URLError as exc:
        print(f"  FAILED: {exc.reason}")
        print()
        return
    except Exception as exc:
        print(f"  FAILED: {type(exc).__name__}: {exc}")
        print()
        return

    print(f"  status: {status}")
    print(f"  final URL: {final_url}")
    print(f"  HTML bytes: {len(html.encode('utf-8'))}")

    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    print(f"  title: {title!r}")

    print()
    print("  RELEVANT LINKS")
    print("  --------------")
    seen = set()
    for a in soup.find_all("a", href=True):
        text = " ".join(a.stripped_strings).strip()
        href = urljoin(final_url, a["href"])
        blob = f"{text} {href}".upper()
        if any(
            key in blob
            for key in (
                "SCORE", "RESULT", "SHOOT", "EVENT", "LIVE",
                "ATA", "TRAP", "SEARCH", "TOURNAMENT"
            )
        ):
            key = (text, href)
            if key in seen:
                continue
            seen.add(key)
            print(f"  {text or '(no text)'} -> {href}")

    print()
    print("  FORMS")
    print("  -----")
    forms = soup.find_all("form")
    if not forms:
        print("  none")
    for i, form in enumerate(forms, 1):
        print(
            f"  form {i}: action={urljoin(final_url, form.get('action') or '')} "
            f"method={(form.get('method') or 'GET').upper()}"
        )
        for ctl in form.find_all(["input","select","button"]):
            print(
                f"    {ctl.name} name={ctl.get('name')!r} "
                f"id={ctl.get('id')!r} value={ctl.get('value')!r} "
                f"type={ctl.get('type')!r}"
            )

    print()
    print("  SCRIPT SOURCES")
    print("  --------------")
    for script in soup.find_all("script", src=True):
        print(f"  {urljoin(final_url, script.get('src'))}")

    print()
    print("  HTML HINTS")
    print("  ----------")
    hints = (
        "score", "result", "shoot", "event", "api/", "graphql",
        "axios", "fetch(", "signalr", "blazor"
    )
    shown = 0
    for line in html.splitlines():
        lower = line.lower()
        if any(h in lower for h in hints):
            compact = re.sub(r"\s+", " ", line).strip()
            if compact:
                print(f"  {compact[:2000]}")
                shown += 1
                if shown >= 25:
                    break

    print()
    print("=" * 72)
    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect public SOS Clays score/result routes."
    )
    parser.add_argument(
        "--url",
        action="append",
        default=[],
        help="Additional SOS Clays URL to inspect.",
    )
    args = parser.parse_args()

    print("MNTrapTeam SOS Clays Public-Score Diagnostic")
    print("============================================")
    print("READ ONLY — no MNTrapTeam database changes.")
    print()

    urls = CANDIDATES + list(args.url)
    for i, url in enumerate(urls, 1):
        inspect(f"[{i}/{len(urls)}]", url)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
