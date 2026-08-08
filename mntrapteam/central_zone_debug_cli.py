from __future__ import annotations

import argparse
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

BASE = "https://www.shootatazone.com/central/"


def fetch(url: str, timeout: int = 10) -> str:
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 MNTrapTeam/4.6.5",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def describe_forms(html: str, base_url: str) -> None:
    soup = BeautifulSoup(html, "html.parser")
    forms = soup.find_all("form")
    print(f"Forms found: {len(forms)}")
    print()

    for idx, form in enumerate(forms, 1):
        action = form.get("action") or ""
        method = (form.get("method") or "GET").upper()
        print(f"FORM {idx}")
        print(f"  action: {urljoin(base_url, action)}")
        print(f"  method: {method}")

        controls = form.find_all(["input", "select", "button", "textarea"])
        for control in controls:
            tag = control.name
            ctype = control.get("type") or ""
            name = control.get("name") or ""
            value = control.get("value") or ""
            print(
                f"  {tag} type={ctype!r} name={name!r} value={value!r}"
            )

            if tag == "select":
                options = []
                for opt in control.find_all("option"):
                    label = " ".join(opt.stripped_strings).strip()
                    options.append((opt.get("value") or "", label))
                for opt_value, label in options[:30]:
                    print(f"    option value={opt_value!r} label={label!r}")

        print()

    print("RELEVANT LINKS")
    print("--------------")
    for anchor in soup.find_all("a", href=True):
        text = " ".join(anchor.stripped_strings).strip()
        href = urljoin(base_url, anchor["href"])
        upper = (text + " " + href).upper()
        if any(
            key in upper
            for key in (
                "SCORE", "ENTRY", "EVENT", "LEADER", "HIGH GUN",
                "SEARCH", "REPORT", "CLUB"
            )
        ):
            print(f"{text or '(no text)'} -> {href}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect ATA Central Zone scoreboard forms and links."
    )
    parser.add_argument(
        "--save-dir",
        default=r".\data\connector_downloads\central_zone_debug",
    )
    args = parser.parse_args()

    save_dir = Path(args.save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    urls = [
        ("menu", urljoin(BASE, "menu.cfm")),
        ("scores", urljoin(BASE, "scores.cfm")),
        ("entries", urljoin(BASE, "entrys.cfm")),
    ]

    print("MNTrapTeam ATA Central Zone Diagnostic")
    print("======================================")
    print("READ ONLY — no MNTrapTeam database changes.")
    print()

    for label, url in urls:
        print(f"Fetching {label}: {url}")
        try:
            html = fetch(url)
        except Exception as exc:
            print(f"  FAILED: {type(exc).__name__}: {exc}")
            print()
            continue

        out = save_dir / f"{label}.html"
        out.write_text(html, encoding="utf-8")
        print(f"  Saved: {out}")
        print()

        if label in {"scores", "entries"}:
            print(f"{label.upper()} PAGE STRUCTURE")
            print("-" * (len(label) + 15))
            describe_forms(html, url)
            print()

    print("Diagnostic complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
