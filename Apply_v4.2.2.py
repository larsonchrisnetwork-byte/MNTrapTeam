from pathlib import Path
import shutil

VERSION = "4.2.2"
SOURCE_ROOT = Path(__file__).resolve().parent
TARGET = Path("mntrapteam/official_baseline.py")

def main():
    if not TARGET.parent.exists():
        raise SystemExit("Run from H:\\MNTrapTeam\\MNTrapTeam")

    src = SOURCE_ROOT / "mntrapteam" / "official_baseline.py"
    if src.resolve() != TARGET.resolve():
        shutil.copy2(src, TARGET)
    else:
        print(f"Skipping self-copy: {TARGET}")

    Path("VERSION").write_text(VERSION + "\n", encoding="utf-8")

    # Keep GUI version consistency test happy.
    gui = Path("mntrapteam/gui.py")
    if gui.exists():
        text = gui.read_text(encoding="utf-8")
        import re
        text = re.sub(
            r"MNTrapTeam \d+\.\d+\.\d+",
            f"MNTrapTeam {VERSION}",
            text,
            count=1,
        )
        gui.write_text(text, encoding="utf-8")

    print("MNTrapTeam 4.2.2 applied.")
    print("Fixed official baseline INSERT: 11 columns now receive exactly 11 values.")

if __name__ == "__main__":
    main()
