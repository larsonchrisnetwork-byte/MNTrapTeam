from urllib.request import Request, urlopen
from bs4 import BeautifulSoup
from pathlib import Path

url = "https://shootscoreboard.com/"

request = Request(
    url,
    headers={
        "User-Agent": "Mozilla/5.0 MNTrapTeam",
        "Accept": "text/html,application/xhtml+xml",
    },
)

html = urlopen(request, timeout=30).read().decode(
    "utf-8",
    errors="replace",
)

Path("exports").mkdir(exist_ok=True)
Path("exports/shootscoreboard_home_raw.html").write_text(
    html,
    encoding="utf-8",
)

soup = BeautifulSoup(html, "html.parser")

print("HTML characters:", len(html))
print()

print("SELECTS:")
for index, select in enumerate(soup.find_all("select"), 1):
    print(
        f"SELECT {index}:",
        "name=", select.get("name"),
        "id=", select.get("id"),
        "onchange=", select.get("onchange"),
    )
    for option in select.find_all("option")[:40]:
        print(
            "   OPTION",
            "value=", option.get("value"),
            "text=", option.get_text(" ", strip=True),
        )

print()
print("FORMS:")
for index, form in enumerate(soup.find_all("form"), 1):
    print(
        f"FORM {index}:",
        "action=", form.get("action"),
        "method=", form.get("method"),
        "id=", form.get("id"),
        "name=", form.get("name"),
    )

print()
print("INPUTS / BUTTONS:")
for field in soup.find_all(["input", "button"]):
    print(
        field.name,
        "type=", field.get("type"),
        "name=", field.get("name"),
        "value=", field.get("value"),
        "id=", field.get("id"),
        "onclick=", field.get("onclick"),
    )

print()
print("LINES CONTAINING 2026:")
for line in html.splitlines():
    if "2026" in line:
        print(line[:1000])
