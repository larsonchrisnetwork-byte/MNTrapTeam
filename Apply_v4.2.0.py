from pathlib import Path
import re
import shutil

VERSION = "4.2.0"
SOURCE_ROOT = Path(__file__).resolve().parent
TARGET_ROOT = Path(".")


def copy_if_needed(src: Path, dst: Path):
    if src.resolve() == dst.resolve():
        print(f"Skipping self-copy: {dst}")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def main():
    pkg = TARGET_ROOT / "mntrapteam"
    if not pkg.exists():
        raise SystemExit("Run from H:\\MNTrapTeam\\MNTrapTeam")

    for name in (
        "official_baseline.py",
        "live_dashboard.py",
        "gui.py",
        "myata_bulk_dom_cli.py",
        "shootscoreboard_web.py",
        "live_import.py",
        "mens_race_cli.py",
    ):
        copy_if_needed(SOURCE_ROOT / "mntrapteam" / name, pkg / name)

    Path("VERSION").write_text(VERSION + "\n", encoding="utf-8")

    init = pkg / "__init__.py"
    if init.exists():
        lines = init.read_text(encoding="utf-8").splitlines()
        for index,line in enumerate(lines):
            if line.strip().startswith("__version__"):
                lines[index] = f'__version__ = "{VERSION}"'
                break
        else:
            lines.append(f'__version__ = "{VERSION}"')
        init.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("MNTrapTeam 4.2.0 applied.")
    print("Men's Team Race now keeps MyATA official totals separate from newer unofficial scores.")
    print("MyATA importer supports --ata-file and records the official-through date.")
    print("ShootScoreBoard public imports support --out-of-state for Grand/other non-MN shoots.")


if __name__ == "__main__":
    main()
