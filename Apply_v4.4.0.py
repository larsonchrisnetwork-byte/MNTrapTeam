from pathlib import Path
import re
import shutil

VERSION = "4.4.0"
SOURCE_ROOT = Path(__file__).resolve().parent
ROOT = Path(".")


def main():
    pkg = ROOT / "mntrapteam"
    if not pkg.exists():
        raise SystemExit("Run from H:\\MNTrapTeam\\MNTrapTeam")

    src = SOURCE_ROOT / "mntrapteam" / "recent_score_scout_cli.py"
    dst = pkg / "recent_score_scout_cli.py"
    if src.resolve() != dst.resolve():
        shutil.copy2(src, dst)
    else:
        print(f"Skipping self-copy: {dst}")

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

    print("MNTrapTeam 4.4.0 applied.")
    print("Added candidate-centric recent ShootScoreBoard score scout.")
    print("Scout does not rebuild or overwrite official MyATA season_stats.")


if __name__ == "__main__":
    main()
