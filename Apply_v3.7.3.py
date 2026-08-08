from pathlib import Path
import re

VERSION = "3.7.3"
TARGET = Path("mntrapteam/myata_mn_enrichment.py")
MASTER = 'MN_CLUB_ALIASES = {\n    "ALEXANDRIA SHOOTING PARK": {"club_id": "MN-MTA-ALEXANDRIA", "name": "Alexandria Shooting Park", "state": "MN"},\n    "BALD EAGLE SPORTSMENS ASSN": {"club_id": "MN-MTA-BALDEAGLE", "name": "Bald Eagle Sportsmen\'s Assn", "state": "MN"},\n    "BEAVERBROOK TRI CO CLUB": {"club_id": "MN-MTA-BEAVERBROOK", "name": "Beaverbrook Tri-Co Club", "state": "MN"},\n    "BEAVER BROOK TRI COUNTY GUN CLUB": {"club_id": "MN-MTA-BEAVERBROOK", "name": "Beaverbrook Tri-Co Club", "state": "MN"},\n    "BECKER CO SPORTSMENS CLUB": {"club_id": "MN-MTA-BECKER", "name": "Becker Co Sportsmens Club", "state": "MN"},\n    "BEMIDJI TRAP AND SKEET CLUB": {"club_id": "MN-MTA-BEMIDJI", "name": "Bemidji Trap & Skeet Club", "state": "MN"},\n    "BUFFALO GUN CLUB": {"club_id": "MN-MTA-BUFFALO", "name": "Buffalo Gun Club", "state": "MN"},\n    "DEL TONE GUN RANGE": {"club_id": "MN-MTA-DELTONE", "name": "Del-Tone Gun Range", "state": "MN"},\n    "DEL TONE SHOOTING RANGE": {"club_id": "MN-MTA-DELTONE", "name": "Del-Tone Gun Range", "state": "MN"},\n    "FAIRMONT TRAP CLUB": {"club_id": "MN-MTA-FAIRMONT", "name": "Fairmont Trap Club Inc", "state": "MN"},\n    "FAIRMONT TRAP CLUB INC": {"club_id": "MN-MTA-FAIRMONT", "name": "Fairmont Trap Club Inc", "state": "MN"},\n    "FOREST LAKE SPORTSMENS CLUB": {"club_id": "MN-MTA-FORESTLAKE", "name": "Forest Lake Sportsmens Club", "state": "MN"},\n    "GLENWOOD GUN CLUB": {"club_id": "MN-MTA-GLENWOOD", "name": "Glenwood Gun Club", "state": "MN"},\n    "GRAND RAPIDS GUN CLUB": {"club_id": "MN-MTA-GRANDRAPIDS", "name": "Grand Rapids Gun Club", "state": "MN"},\n    "MN CLAY TARGET SPORTS GRAND RAPIDS": {"club_id": "MN-MTA-GRANDRAPIDS", "name": "Grand Rapids Gun Club", "state": "MN"},\n    "HIBBING TRAP CLUB": {"club_id": "MN-MTA-HIBBING", "name": "Hibbing Trap Club", "state": "MN"},\n    "HUNTERSVILLE SPORTSMENS PARK": {"club_id": "MN-MTA-HUNTERSVILLE", "name": "Huntersville Sportsmen\'s Park", "state": "MN"},\n    "LAKESHORE CONSERVATION CLUB": {"club_id": "MN-MTA-LAKESHORE", "name": "Lakeshore Conservation Club", "state": "MN"},\n    "LESTER PRAIRIE SPORTSMENS CLUB": {"club_id": "MN-MTA-LESTERPRAIRIE", "name": "Lester Prairie Sportsmens Club", "state": "MN"},\n    "MINNEAPOLIS GUN CLUB": {"club_id": "MN-MTA-MINNEAPOLIS", "name": "Minneapolis Gun Club", "state": "MN"},\n    "MINNESOTA SPORTSMENS CLUB ZIMMERMAN": {"club_id": "MN-MTA-ZIMMERMAN", "name": "Minnesota Sportsmens Club (Zimmerman)", "state": "MN"},\n    "MINNESOTA YOUTH SHOTGUN ASSN": {"club_id": "MN-MTA-MYSA", "name": "Minnesota Youth Shotgun Assn", "state": "MN"},\n    "MINNESOTA TRAP ASSOCIATION": {"club_id": "MN-MTA-MTA", "name": "Minnesota Trap Association", "state": "MN"},\n    "MINNESOTA TRAP ASSN": {"club_id": "MN-MTA-MTA", "name": "Minnesota Trap Association", "state": "MN"},\n    "MONTICELLO ROD AND GUN CLUB": {"club_id": "MN-MTA-MONTICELLORG", "name": "Monticello Rod & Gun Club", "state": "MN"},\n    "MONTICELLO SPORTSMENS CLUB": {"club_id": "MN-MTA-MONTICELLO", "name": "Monticello Sportsmens Club", "state": "MN"},\n    "MORRISTOWN GUN CLUB": {"club_id": "MN-MTA-MORRISTOWN", "name": "Morristown Gun Club", "state": "MN"},\n    "OWATONNA GUN CLUB": {"club_id": "MN-MTA-OWATONNA", "name": "Owatonna Gun Club", "state": "MN"},\n    "PROCTOR JACK MEAD GUN CLUB": {"club_id": "MN-MTA-PROCTOR", "name": "Proctor Jack Mead Gun Club", "state": "MN"},\n    "SHOOTERS SPORTING CLAYS MARSHALL": {"club_id": "MN-MTA-MARSHALL", "name": "Shooters Sporting Clays (Marshall)", "state": "MN"},\n    "WATERTOWN ROD AND GUN CLUB": {"club_id": "MN-MTA-WATERTOWN", "name": "Watertown Rod & Gun Club", "state": "MN"},\n    "WINONA SPORTSMENS CLUB": {"club_id": "MN-MTA-WINONA", "name": "Winona Sportsmens Club", "state": "MN"},\n}\n'

def main():
    if not TARGET.exists():
        raise SystemExit("Run from H:\\MNTrapTeam\\MNTrapTeam")

    text = TARGET.read_text(encoding="utf-8")
    start = text.find("MN_CLUB_ALIASES = {")
    if start == -1:
        raise RuntimeError("MN_CLUB_ALIASES table not found. Apply v3.7.1/v3.7.2 first.")

    brace = text.find("{", start)
    depth = 0
    end = None
    for i in range(brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    if end is None:
        raise RuntimeError("Could not parse MN_CLUB_ALIASES dictionary.")

    text = text[:start] + MASTER + text[end:]
    compile(text, str(TARGET), "exec")
    TARGET.write_text(text, encoding="utf-8")

    Path("VERSION").write_text(VERSION + "\n", encoding="utf-8")

    gui = Path("mntrapteam/gui.py")
    if gui.exists():
        g = gui.read_text(encoding="utf-8")
        g = re.sub(r"MNTrapTeam \d+\.\d+\.\d+", f"MNTrapTeam {VERSION}", g, count=1)
        gui.write_text(g, encoding="utf-8")

    init = Path("mntrapteam/__init__.py")
    if init.exists():
        lines = init.read_text(encoding="utf-8").splitlines()
        for idx, line in enumerate(lines):
            if line.strip().startswith("__version__"):
                lines[idx] = f'__version__ = "{VERSION}"'
                break
        else:
            lines.append(f'__version__ = "{VERSION}"')
        init.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("MNTrapTeam 3.7.3 applied: authoritative MTA Minnesota club whitelist installed.")

if __name__ == "__main__":
    main()
