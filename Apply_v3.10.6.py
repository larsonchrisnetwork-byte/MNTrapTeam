from pathlib import Path
import re
import shutil

VERSION = "3.10.6"
ROOT = Path(".")
TARGET = ROOT / "mntrapteam" / "zone_haa_south_verify_cli.py"
CONFIG = ROOT / "config"

def main():
    if not TARGET.exists():
        raise SystemExit("Run from H:\\MNTrapTeam\\MNTrapTeam")

    source_root = Path(__file__).resolve().parent

    CONFIG.mkdir(exist_ok=True)
    shutil.copy2(
        source_root / "config" / "mta_zone_counties.json",
        CONFIG / "mta_zone_counties.json",
    )
    shutil.copy2(
        source_root / "config" / "mn_city_county_overrides.json",
        CONFIG / "mn_city_county_overrides.json",
    )
    shutil.copy2(
        source_root / "mntrapteam" / "zone_haa_south_verify_cli.py",
        TARGET,
    )

    Path("VERSION").write_text(VERSION + "\n", encoding="utf-8")

    gui = Path("mntrapteam/gui.py")
    if gui.exists():
        text = gui.read_text(encoding="utf-8")
        text = re.sub(
            r"MNTrapTeam \d+\.\d+\.\d+",
            f"MNTrapTeam {VERSION}",
            text,
            count=1,
        )
        gui.write_text(text, encoding="utf-8")

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
        "MNTrapTeam 3.10.6 applied: Carver County corrected to Southern, "
        "zone mappings moved to config, and city normalization added."
    )

if __name__ == "__main__":
    main()
