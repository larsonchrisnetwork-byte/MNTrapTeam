from __future__ import annotations

import argparse
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup


UA = "Mozilla/5.0 MNTrapTeam/4.9.5"


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


def inspect(url: str, label: str) -> list[str]:
    print(label)
    print("-" * len(label))
    print(url)

    final_url, html = fetch(url)
    soup = BeautifulSoup(html, "html.parser")

    print(f"Final URL: {final_url}")
    print(f"HTML bytes: {len(html.encode('utf-8'))}")
    print(f"Title: {soup.title.get_text(' ', strip=True) if soup.title else ''!r}")
    print()

    print("VISIBLE TEXT")
    print("------------")
    print(" ".join(soup.stripped_strings)[:8000])
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
        for ctl in form.find_all(["input","select","button"]):
            print(
                f"  {ctl.name} name={ctl.get('name')!r} "
                f"id={ctl.get('id')!r} value={ctl.get('value')!r} "
                f"type={ctl.get('type')!r} onclick={ctl.get('onclick')!r}"
            )
            if ctl.name == "select":
                for opt in ctl.find_all("option")[:100]:
                    val = opt.get("value") or ""
                    txt = " ".join(opt.stripped_strings).strip()
                    print(f"    option value={val!r} label={txt!r}")
    print()

    print("ALL LINKS")
    print("---------")
    links = []
    for a in soup.find_all("a", href=True):
        text = " ".join(a.stripped_strings).strip()
        href = urljoin(final_url, a["href"])
        links.append(href)
        print(f"{text or '(no text)'} -> {href}")
    print()

    print("IFRAMES")
    print("-------")
    for frame in soup.find_all("iframe", src=True):
        print(urljoin(final_url, frame["src"]))
    print()
    print("=" * 72)
    print()
    return links


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--club-id", type=int, default=161)
    parser.add_argument("--program-id", type=int, default=4705)
    args = parser.parse_args()

    print("MNTrapTeam ScoresR Club Shoot-List Diagnostic")
    print("=============================================")
    print("READ ONLY — no database changes.")
    print()

    url = (
        "https://www.scoresr.com/regv2/PublicIfShowClubShoots.php"
        f"?clubId={args.club_id}&programId={args.program_id}"
    )

    links = inspect(url, "CLUB SHOOT LIST IFRAME")

    relevant = [
        link for link in links
        if any(k in link.lower() for k in ("shoot", "score", "result", "report", "event"))
    ]

    print("LIKELY SCORE/SHOOT ROUTES")
    print("-------------------------")
    if not relevant:
        print("None found.")
    else:
        for link in relevant[:50]:
            print(link)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
