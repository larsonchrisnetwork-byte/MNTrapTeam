from pathlib import Path
import shutil
import re

VERSION = "4.3.0"
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
        "mens_race_cli.py",
        "live_dashboard.py",
        "gui.py",
        "mens_baseline_targets_cli.py",
    ):
        copy_if_needed(SOURCE_ROOT / "mntrapteam" / name, pkg / name)

    Path("VERSION").write_text(VERSION + "\n", encoding="utf-8")

    init = pkg / "__init__.py"
    if init.exists():
        lines = init.read_text(encoding="utf-8-sig").splitlines()
        found = False
        for index,line in enumerate(lines):
            if line.strip().startswith("__version__"):
                lines[index] = f'__version__ = "{VERSION}"'
                found = True
                break
        if not found:
            lines.append(f'__version__ = "{VERSION}"')
        init.write_text("\n".join(lines) + "\n", encoding="utf-8")

    gui = pkg / "gui.py"
    if gui.exists():
        text = gui.read_text(encoding="utf-8-sig")
        text = re.sub(
            r"MNTrapTeam \d+\.\d+\.\d+",
            f"MNTrapTeam {VERSION}",
            text,
            count=1,
        )
        gui.write_text(text, encoding="utf-8")

    print("MNTrapTeam 4.3.0 applied.")
    print("Men's race CLI now uses the project's actual RulesEngine + TeamService.")
    print("Live Team adds a Baseline Ready column.")
    print("Added Men's HAA baseline refresh-list generator.")


if __name__ == "__main__":
    main()
