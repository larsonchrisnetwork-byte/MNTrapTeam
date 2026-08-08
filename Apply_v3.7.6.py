from pathlib import Path
import re

VERSION = "3.7.6"
TARGET = Path("mntrapteam/myata_mn_enrichment.py")

OLD = '        if not normalized:\n            return ClubMatch(raw_name=raw, method="blank")\n\n        alias = self.mn_aliases.get(normalized)\n'
NEW = '        if not normalized:\n            return ClubMatch(raw_name=raw, method="blank")\n\n        # Hard authoritative MTA overrides for MyATA spellings that have\n        # repeatedly bypassed alias/fuzzy matching in production.\n        hard_mn = {\n            "BEMIDJI TRAP AND SKEET GUN CLUB": (\n                "MN-MTA-BEMIDJI", "Bemidji Trap & Skeet Club"\n            ),\n            "BEMIDJI TRAP AND SKEET CLUB": (\n                "MN-MTA-BEMIDJI", "Bemidji Trap & Skeet Club"\n            ),\n            "FAIRMONT TRAP CLUB INC": (\n                "MN-MTA-FAIRMONT", "Fairmont Trap Club Inc"\n            ),\n            "FOREST LAKE SPORTSMENS CLUB": (\n                "MN-MTA-FORESTLAKE", "Forest Lake Sportsmens Club"\n            ),\n        }\n\n        override = hard_mn.get(normalized)\n        if override:\n            club_id, canonical_name = override\n            return ClubMatch(\n                raw_name=raw,\n                canonical_name=canonical_name,\n                state="MN",\n                club_id=club_id,\n                score=100.0,\n                method="mta-hard-override",\n                confident=True,\n            )\n\n        alias = self.mn_aliases.get(normalized)\n'

def main():
    if not TARGET.exists():
        raise SystemExit("Run from H:\\MNTrapTeam\\MNTrapTeam")

    text = TARGET.read_text(encoding="utf-8")

    if OLD in text:
        text = text.replace(OLD, NEW, 1)
    elif NEW not in text:
        raise RuntimeError("Could not find club matcher insertion point.")

    compile(text, str(TARGET), "exec")
    TARGET.write_text(text, encoding="utf-8")

    Path("VERSION").write_text(VERSION + "\n", encoding="utf-8")

    gui = Path("mntrapteam/gui.py")
    if gui.exists():
        g = gui.read_text(encoding="utf-8")
        g = re.sub(
            r"MNTrapTeam \d+\.\d+\.\d+",
            f"MNTrapTeam {VERSION}",
            g,
            count=1,
        )
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

    print(
        "MNTrapTeam 3.7.6 applied: hard MTA overrides added for "
        "Bemidji, Fairmont, and Forest Lake."
    )

if __name__ == "__main__":
    main()
