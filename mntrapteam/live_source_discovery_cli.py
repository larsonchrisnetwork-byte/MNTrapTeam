
from __future__ import annotations

import argparse
import re
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup


UA = "Mozilla/5.0 MNTrapTeam/4.9.1"


def fetch(url: str, timeout: int = 12) -> tuple[str, str]:
    req = Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,*/*",
        },
    )
    with urlopen(req, timeout=timeout) as response:
        return response.geturl(), response.read().decode("utf-8", errors="replace")


def inspect_sos() -> None:
    print("SOS CLAYS")
    print("=========")

    page_url = "https://www.sosclays.com/shoots"
    final_url, html = fetch(page_url)
    soup = BeautifulSoup(html, "html.parser")

    scripts = [
        urljoin(final_url, s.get("src"))
        for s in soup.find_all("script", src=True)
        if s.get("src")
    ]

    print(f"Page: {final_url}")
    print(f"JS chunks found: {len(scripts)}")
    print()

    api_hints = set()
    route_hints = set()

    patterns = [
        r'["\'](/api/[^"\'\\\s]+)["\']',
        r'["\'](https?://[^"\'\\\s]+)["\']',
        r'fetch\(\s*["\']([^"\']+)["\']',
        r'axios\.(?:get|post)\(\s*["\']([^"\']+)["\']',
    ]

    for script_url in scripts:
        try:
            _, js = fetch(script_url)
        except Exception:
            continue

        lower = js.lower()
        if not any(k in lower for k in ("shoot", "result", "score", "api/")):
            continue

        for pat in patterns:
            for match in re.findall(pat, js, flags=re.I):
                value = match.replace("\\/", "/")
                if "/api/" in value or "sosclays" in value.lower():
                    api_hints.add(value)

        for match in re.findall(
            r'["\'](/(?:shoots|state-shoots|past-results)[^"\'\\\s]*)["\']',
            js,
            flags=re.I,
        ):
            route_hints.add(match.replace("\\/", "/"))

    print("API / DATA HINTS")
    print("----------------")
    if not api_hints:
        print("None found in static chunks.")
    else:
        for item in sorted(api_hints):
            print(item)

    print()
    print("ROUTE HINTS")
    print("-----------")
    if not route_hints:
        print("None found.")
    else:
        for item in sorted(route_hints):
            print(item)

    print()
    print("VISIBLE SHOOT LINKS")
    print("-------------------")
    seen = set()
    for a in soup.find_all("a", href=True):
        href = urljoin(final_url, a["href"])
        text = " ".join(a.stripped_strings).strip()
        if "/shoots/" in href and href not in seen:
            seen.add(href)
            print(f"{text or '(no text)'} -> {href}")

    print()
    print("=" * 72)
    print()


def inspect_scoresr() -> None:
    print("SCORESR")
    print("=======")

    urls = [
        "https://www.scoresr.com/",
        "https://www.scoresr.com/ClubFinderA.php",
    ]

    for url in urls:
        print(f"Page: {url}")
        try:
            final_url, html = fetch(url)
        except Exception as exc:
            print(f"  FAILED: {type(exc).__name__}: {exc}")
            print()
            continue

        soup = BeautifulSoup(html, "html.parser")

        print("FORMS")
        print("-----")
        forms = soup.find_all("form")
        if not forms:
            print("none")
        for i, form in enumerate(forms, 1):
            print(
                f"form {i}: action={urljoin(final_url, form.get('action') or '')} "
                f"method={(form.get('method') or 'GET').upper()}"
            )
            for ctl in form.find_all(["input", "select", "button"]):
                print(
                    f"  {ctl.name} name={ctl.get('name')!r} "
                    f"id={ctl.get('id')!r} value={ctl.get('value')!r} "
                    f"type={ctl.get('type')!r}"
                )
                if ctl.name == "select":
                    for opt in ctl.find_all("option")[:80]:
                        label = " ".join(opt.stripped_strings).strip()
                        value = opt.get("value") or ""
                        if label or value:
                            print(f"    option value={value!r} label={label!r}")

        print()
        print("RELEVANT LINKS")
        print("--------------")
        seen = set()
        for a in soup.find_all("a", href=True):
            text = " ".join(a.stripped_strings).strip()
            href = urljoin(final_url, a["href"])
            blob = f"{text} {href}".upper()
            if any(
                key in blob
                for key in (
                    "PAST", "SCORE", "SHOOT", "CLUB", "ATA",
                    "RESULT", "PUBLICVIEW", "REGV2"
                )
            ):
                key = (text, href)
                if key in seen:
                    continue
                seen.add(key)
                print(f"{text or '(no text)'} -> {href}")

        print()
        print("-" * 72)

    print()
    print("Known current fact: ScoresR only covers clubs using ScoresR services.")
    print("=" * 72)
    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only source discovery for SOS Clays and ScoresR."
    )
    parser.add_argument(
        "--source",
        choices=("all", "sos", "scoresr"),
        default="all",
    )
    args = parser.parse_args()

    print("MNTrapTeam Live Source Discovery")
    print("================================")
    print("READ ONLY — no MNTrapTeam database changes.")
    print()

    if args.source in ("all", "sos"):
        inspect_sos()
    if args.source in ("all", "scoresr"):
        inspect_scoresr()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
