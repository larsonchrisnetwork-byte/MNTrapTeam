from __future__ import annotations

import argparse
import re
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup


UA = "Mozilla/5.0 MNTrapTeam/4.9.4"


def fetch(url: str, timeout: int = 12):
    req = Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,*/*",
        },
    )
    with urlopen(req, timeout=timeout) as response:
        return response.geturl(), response.read().decode("utf-8", errors="replace")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--club-id", type=int, default=161)
    parser.add_argument("--program-id", type=int, default=4705)
    parser.add_argument("--club-name", default="Minneapolis Gun Club Inc")
    args = parser.parse_args()

    club_name_q = args.club_name.replace(" ", "+")
    url = (
        "https://www.scoresr.com/regv2/PublicViewShoot.php"
        f"?clubId={args.club_id}&p={args.program_id}&name={club_name_q}"
    )

    print("MNTrapTeam ScoresR PublicViewShoot Deep Diagnostic")
    print("==================================================")
    print("READ ONLY — no database changes.")
    print(url)
    print()

    final_url, html = fetch(url)
    soup = BeautifulSoup(html, "html.parser")

    print(f"Final URL: {final_url}")
    print(f"HTML bytes: {len(html.encode('utf-8'))}")
    print(f"Title: {soup.title.get_text(' ', strip=True) if soup.title else ''!r}")
    print()

    print("VISIBLE TEXT")
    print("------------")
    text = " ".join(soup.stripped_strings)
    print(text[:5000])
    print()

    print("FORMS")
    print("-----")
    forms = soup.find_all("form")
    print(f"Count: {len(forms)}")
    for i, form in enumerate(forms, 1):
        print(
            f"form {i}: action={urljoin(final_url, form.get('action') or '')} "
            f"method={(form.get('method') or 'GET').upper()}"
        )
        for ctl in form.find_all(["input","select","button","textarea"]):
            print(
                f"  {ctl.name} name={ctl.get('name')!r} id={ctl.get('id')!r} "
                f"value={ctl.get('value')!r} type={ctl.get('type')!r} "
                f"onclick={ctl.get('onclick')!r}"
            )
            if ctl.name == "select":
                for opt in ctl.find_all("option")[:100]:
                    val = opt.get("value") or ""
                    txt = " ".join(opt.stripped_strings).strip()
                    print(f"    option value={val!r} label={txt!r}")
    print()

    print("BUTTONS")
    print("-------")
    for b in soup.find_all(["button","input"]):
        if b.name == "input" and b.get("type") not in ("submit","button","radio","checkbox"):
            continue
        print(
            f"{b.name} text={' '.join(b.stripped_strings).strip()!r} "
            f"name={b.get('name')!r} value={b.get('value')!r} "
            f"type={b.get('type')!r} onclick={b.get('onclick')!r}"
        )
    print()

    print("SCRIPT SOURCES")
    print("--------------")
    for s in soup.find_all("script", src=True):
        print(urljoin(final_url, s["src"]))
    print()

    print("INLINE SCRIPT / HTML ENDPOINT HINTS")
    print("-----------------------------------")
    hints = ("ShootIC", "PublicView", "Score", "Result", "Report", "Event", "ajax", "$.post", "$.get", "fetch(", "location.href")
    shown = 0
    for line in html.splitlines():
        if any(h.lower() in line.lower() for h in hints):
            compact = re.sub(r"\s+", " ", line).strip()
            if compact:
                print(compact[:3000])
                shown += 1
                if shown >= 60:
                    break

    print()
    print("ALL LINKS")
    print("---------")
    for a in soup.find_all("a", href=True):
        print(f"{' '.join(a.stripped_strings).strip() or '(no text)'} -> {urljoin(final_url, a['href'])}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
