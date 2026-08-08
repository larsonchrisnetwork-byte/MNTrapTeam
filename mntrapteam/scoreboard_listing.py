from __future__ import annotations

from dataclasses import dataclass
from html import unescape
from urllib.parse import urlencode, urljoin, urlparse, parse_qs
from urllib.request import Request, urlopen
import re

from bs4 import BeautifulSoup


HOME = "https://shootscoreboard.com/"

ZONE_MATCHERS = {
    "SOUTHERN": (
        "SOUTHERN ZONE",
        "LESTER PRAIRIE",
    ),
    "CENTRAL": (
        "CENTRAL ZONE",
        "BEAVERBROOK",
    ),
    "NORTHERN": (
        "NORTHERN ZONE",
        "GRAND RAPIDS",
    ),
}


@dataclass
class ListedShoot:
    shoot_id: int
    name: str
    text: str
    href: str
    zone: str = ""


def fetch_html(url: str, data: bytes | None = None) -> str:
    request = Request(
        url,
        data=data,
        headers={
            "User-Agent": "Mozilla/5.0 MNTrapTeam",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def _form_with_year(soup: BeautifulSoup, year: int):
    target = str(year)
    for form in soup.find_all("form"):
        for select in form.find_all("select"):
            for option in select.find_all("option"):
                value = str(option.get("value") or "").strip()
                label = " ".join(option.get_text(" ", strip=True).split())
                if value == target or label == target:
                    return form, select, option
    return None, None, None


def _successful_controls(form, selected_name: str, selected_value: str) -> dict[str, str]:
    values: dict[str, str] = {}

    for field in form.find_all(["input", "select"]):
        name = field.get("name")
        if not name:
            continue

        if field.name == "select":
            if name == selected_name:
                values[name] = selected_value
                continue

            selected = field.find("option", selected=True)
            if selected is not None:
                values[name] = str(selected.get("value") or selected.get_text(strip=True))
            continue

        field_type = str(field.get("type") or "text").lower()
        if field_type in {"submit", "button", "image", "file"}:
            continue
        if field_type in {"checkbox", "radio"} and not field.has_attr("checked"):
            continue

        values[name] = str(field.get("value") or "")

    values[selected_name] = selected_value
    return values


def fetch_year_listing(year: int = 2026, home_html: str | None = None) -> str:
    html = home_html if home_html is not None else fetch_html(HOME)
    soup = BeautifulSoup(html, "html.parser")
    form, select, option = _form_with_year(soup, year)

    if form is None or select is None or option is None:
        raise RuntimeError(
            f"Could not find a ShootScoreBoard homepage form containing year {year}"
        )

    select_name = select.get("name")
    if not select_name:
        raise RuntimeError("The ShootScoreBoard year select has no field name")

    selected_value = str(option.get("value") or option.get_text(strip=True))
    controls = _successful_controls(form, select_name, selected_value)

    action = form.get("action") or HOME
    target = urljoin(HOME, action)
    method = str(form.get("method") or "get").lower()

    if method == "post":
        return fetch_html(
            target,
            urlencode(controls).encode("utf-8"),
        )

    separator = "&" if "?" in target else "?"
    return fetch_html(target + separator + urlencode(controls))


def _shoot_id_from_href(href: str) -> int | None:
    absolute = urljoin(HOME, href)
    parsed = urlparse(absolute)
    query = parse_qs(parsed.query)
    values = query.get("shootid") or query.get("shootId")
    if values:
        try:
            return int(values[0])
        except (TypeError, ValueError):
            return None

    match = re.search(r"shootid=(\d+)", href, re.I)
    return int(match.group(1)) if match else None


def parse_listing(html: str) -> list[ListedShoot]:
    soup = BeautifulSoup(html, "html.parser")
    results: dict[int, ListedShoot] = {}

    for link in soup.find_all("a", href=True):
        href = str(link.get("href") or "")
        shoot_id = _shoot_id_from_href(href)
        if shoot_id is None:
            continue

        row = link.find_parent("tr")
        context = row.get_text(" ", strip=True) if row else link.parent.get_text(" ", strip=True)
        context = " ".join(unescape(context).split())
        name = " ".join(link.get_text(" ", strip=True).split()) or context

        previous = results.get(shoot_id)
        if previous is None or len(context) > len(previous.text):
            results[shoot_id] = ListedShoot(
                shoot_id=shoot_id,
                name=name,
                text=context,
                href=urljoin(HOME, href),
            )

    return list(results.values())


def classify_zone(text: str) -> str:
    upper = " ".join(str(text or "").upper().split())
    if "2026" not in upper:
        return ""
    if not any(token in upper for token in ("06/", "JUNE", "6/")):
        # Some listings omit a written month; host + zone still remains enough.
        pass

    for zone, hints in ZONE_MATCHERS.items():
        if any(hint in upper for hint in hints):
            return zone
    return ""


def discover_zone_shoots(year: int = 2026) -> list[ListedShoot]:
    listing_html = fetch_year_listing(year)
    shoots = parse_listing(listing_html)

    found: dict[str, ListedShoot] = {}
    for shoot in shoots:
        zone = classify_zone(shoot.text + " " + shoot.name)
        if zone:
            shoot.zone = zone
            found.setdefault(zone, shoot)

    return [
        found[zone]
        for zone in ("SOUTHERN", "CENTRAL", "NORTHERN")
        if zone in found
    ]
