from __future__ import annotations

import argparse
import re
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

BASE = "https://scores.shootata.com/"
DEFAULT_SHOOT_ID = 1331


def fetch(url: str, timeout: int = 10) -> str:
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 MNTrapTeam/4.8.0",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only diagnostic for official ATA Grand score site."
    )
    parser.add_argument("--shoot-id", type=int, default=DEFAULT_SHOOT_ID)
    args = parser.parse_args()

    shoot_id = args.shoot_id
    shoot_url = f"{BASE}shoot/{shoot_id}"
    event1_url = f"{BASE}shoot/{shoot_id}/1"

    print("MNTrapTeam Grand American Diagnostic")
    print("====================================")
    print("READ ONLY — no database changes.")
    print(f"Shoot ID: {shoot_id}")
    print()

    for label, url in (("shoot", shoot_url), ("event1", event1_url)):
        print(f"Fetching {label}: {url}")
        html = fetch(url)
        soup = BeautifulSoup(html, "html.parser")

        print(f"  title: {' '.join(soup.stripped_strings)[:180]}")
        print()

        print("  SELECT OPTIONS")
        print("  --------------")
        found_select = False
        for select in soup.find_all("select"):
            found_select = True
            print(f"  select name={select.get('name')!r} id={select.get('id')!r}")
            for opt in select.find_all("option"):
                value = opt.get("value") or ""
                text = " ".join(opt.stripped_strings).strip()
                print(f"    value={value!r} text={text!r}")
        if not found_select:
            print("  none")

        print()
        print("  EVENT-LIKE LINKS")
        print("  ----------------")
        seen = set()
        for a in soup.find_all("a", href=True):
            href = urljoin(url, a["href"])
            text = " ".join(a.stripped_strings).strip()
            if (
                f"/shoot/{shoot_id}/" in href
                or re.search(r"\bEVENT\b|\bPRELIM|\bGRAND\b", text, re.I)
            ):
                key = (href, text)
                if key in seen:
                    continue
                seen.add(key)
                print(f"  {text or '(no text)'} -> {href}")

        print()
        print("  FORM CONTROLS")
        print("  -------------")
        forms = soup.find_all("form")
        if not forms:
            print("  none")
        for i, form in enumerate(forms, 1):
            print(
                f"  form {i}: action={urljoin(url, form.get('action') or '')} "
                f"method={(form.get('method') or 'GET').upper()}"
            )
            for ctl in form.find_all(["input","button","select"]):
                print(
                    f"    {ctl.name} name={ctl.get('name')!r} "
                    f"value={ctl.get('value')!r} type={ctl.get('type')!r}"
                )
        print()
        print("=" * 60)
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
