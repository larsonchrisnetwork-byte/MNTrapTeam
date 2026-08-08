
from __future__ import annotations

import argparse
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup


UA = "Mozilla/5.0 MNTrapTeam/4.9.2"


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


def inspect(url: str, label: str) -> list[str]:
    print(label)
    print("-" * len(label))
    print(url)

    final_url, html = fetch(url)
    soup = BeautifulSoup(html, "html.parser")
    print(f"Final URL: {final_url}")
    print(f"HTML bytes: {len(html.encode('utf-8'))}")
    print()

    links = []
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
                "RESULT", "SCORE", "REPORT", "EVENT", "HIGH",
                "PUBLICIFSHOW", "SHOOTIC", "ROLLING", "ATA"
            )
        ):
            pair = (text, href)
            if pair in seen:
                continue
            seen.add(pair)
            links.append(href)
            print(f"{text or '(no text)'} -> {href}")

    print()
    print("FORMS")
    print("-----")
    for i, form in enumerate(soup.find_all("form"), 1):
        print(
            f"form {i}: action={urljoin(final_url, form.get('action') or '')} "
            f"method={(form.get('method') or 'GET').upper()}"
        )
        for ctl in form.find_all(["input","select","button"]):
            print(
                f"  {ctl.name} name={ctl.get('name')!r} "
                f"id={ctl.get('id')!r} value={ctl.get('value')!r} "
                f"type={ctl.get('type')!r}"
            )
            if ctl.name == "select":
                for opt in ctl.find_all("option")[:80]:
                    val = opt.get("value") or ""
                    txt = " ".join(opt.stripped_strings).strip()
                    print(f"    option value={val!r} label={txt!r}")
    print()
    print("=" * 72)
    print()
    return links


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect public ScoresR score/report routes."
    )
    parser.add_argument("--club-id", type=int, default=161)
    parser.add_argument("--program-id", type=int, default=4705)
    parser.add_argument(
        "--club-name",
        default="Minneapolis Gun Club Inc",
    )
    args = parser.parse_args()

    print("MNTrapTeam ScoresR Public Report Diagnostic")
    print("===========================================")
    print("READ ONLY — no MNTrapTeam database changes.")
    print()

    club_name_q = args.club_name.replace(" ", "+")
    program = (
        "https://www.scoresr.com/regv2/PublicIfShowShootProgram.php"
        f"?clubId={args.club_id}&programId={args.program_id}"
        f"&clubName={club_name_q}"
    )
    main = (
        "https://www.scoresr.com/regv2/ShootICMain.php"
        f"?forwardClubId={args.club_id}"
        f"&forwardProgramId={args.program_id}"
        f"&forwardClubName={club_name_q}&"
    )

    inspect(program, "PUBLIC SHOOT PROGRAM")
    inspect(main, "PUBLIC SCORE / REPORT HUB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
