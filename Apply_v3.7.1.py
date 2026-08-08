from pathlib import Path
import re

VERSION = "3.7.1"
TARGET = Path("mntrapteam/myata_mn_enrichment.py")
ALIASES = 'MN_CLUB_ALIASES = {\n    "MINNESOTA TRAP ASSOCIATION": {"club_id":"MN-MTA","name":"Minnesota Trap Association","state":"MN"},\n    "BEAVER BROOK TRI COUNTY GUN CLUB": {"club_id":"MN-BEAVERBROOK","name":"Beaver Brook Tri-County Gun Club","state":"MN"},\n    "BEMIDJI TRAP AND SKEET GUN CLUB": {"club_id":"MN-BEMIDJI","name":"Bemidji Trap and Skeet Gun Club","state":"MN"},\n    "MN CLAY TARGET SPORTS GRAND RAPIDS": {"club_id":"MN-GRANDRAPIDS","name":"MN Clay Target Sports (Grand Rapids)","state":"MN"},\n}\n'
OLD_MATCH = '    def match(self, raw_name: str) -> ClubMatch:\n        raw = str(raw_name or "").strip()\n        normalized = normalize_club_name(raw)\n\n        if not normalized:\n            return ClubMatch(raw_name=raw, method="blank")\n\n        exact = self.by_normalized.get(normalized, [])\n'
NEW_MATCH = '    def match(self, raw_name: str) -> ClubMatch:\n        raw = str(raw_name or "").strip()\n        normalized = normalize_club_name(raw)\n\n        if not normalized:\n            return ClubMatch(raw_name=raw, method="blank")\n\n        alias = MN_CLUB_ALIASES.get(normalized)\n        if alias:\n            return ClubMatch(\n                raw_name=raw,\n                canonical_name=alias["name"],\n                state=alias["state"],\n                club_id=alias["club_id"],\n                score=100.0,\n                method="mn-alias",\n                confident=True,\n            )\n\n        exact = self.by_normalized.get(normalized, [])\n'

def main():
    if not TARGET.exists():
        raise SystemExit("Run from H:\\MNTrapTeam\\MNTrapTeam")

    text = TARGET.read_text(encoding="utf-8")

    if "MN_CLUB_ALIASES =" not in text:
        marker = "\n\n@dataclass\nclass ClubMatch:"
        if marker not in text:
            raise RuntimeError("Could not find ClubMatch insertion point.")
        text = text.replace(marker, "\n\n" + ALIASES + marker, 1)

    if OLD_MATCH in text:
        text = text.replace(OLD_MATCH, NEW_MATCH, 1)
    elif NEW_MATCH not in text:
        raise RuntimeError("Could not find SOSClubDirectory.match() block.")

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
        for i, line in enumerate(lines):
            if line.strip().startswith("__version__"):
                lines[i] = f'__version__ = "{VERSION}"'
                break
        else:
            lines.append(f'__version__ = "{VERSION}"')
        init.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("MNTrapTeam 3.7.1 applied: Minnesota club aliases added.")

if __name__ == "__main__":
    main()
