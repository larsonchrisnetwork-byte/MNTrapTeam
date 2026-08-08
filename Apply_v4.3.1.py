from pathlib import Path
import re
import shutil

VERSION = "4.3.1"
SOURCE_ROOT = Path(__file__).resolve().parent
ROOT = Path(".")


def copy_if_needed(src: Path, dst: Path):
    if src.resolve() == dst.resolve():
        print(f"Skipping self-copy: {dst}")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def main():
    pkg = ROOT / "mntrapteam"
    if not pkg.exists():
        raise SystemExit("Run from H:\\MNTrapTeam\\MNTrapTeam")

    for name in (
        "rules.py",
        "state_team_lock.py",
        "state_team_lock_cli.py",
        "live_dashboard.py",
        "mens_baseline_targets_cli.py",
    ):
        copy_if_needed(SOURCE_ROOT / "mntrapteam" / name, pkg / name)

    Path("VERSION").write_text(VERSION + "\n", encoding="utf-8")

    init = pkg / "__init__.py"
    if init.exists():
        text = init.read_text(encoding="utf-8-sig")
        if "__version__" in text:
            text = re.sub(
                r'__version__\s*=\s*["\'][^"\']+["\']',
                f'__version__ = "{VERSION}"',
                text,
                count=1,
            )
        else:
            text += f'\n__version__ = "{VERSION}"\n'
        init.write_text(text, encoding="utf-8")

    gui = pkg / "gui.py"
    if gui.exists():
        text = gui.read_text(encoding="utf-8-sig")
        text = re.sub(r"MNTrapTeam \d+\.\d+\.\d+", f"MNTrapTeam {VERSION}", text, count=1)
        gui.write_text(text, encoding="utf-8")

    print("MNTrapTeam 4.3.1 applied.")
    print("Fixed HAA-category mappings including SBV/L1/L2/V/SRV/J/SJ.")
    print("Added preview/write State Team qualification lock.")
    print("Live State Team race now hides shooters outside the closed HAA gate.")


if __name__ == "__main__":
    main()
