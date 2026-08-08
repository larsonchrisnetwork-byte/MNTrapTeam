from pathlib import Path
import shutil
import re

VERSION = "4.3.2"
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

    copy_if_needed(
        SOURCE_ROOT / "mntrapteam" / "myata_bulk_dom_cli.py",
        pkg / "myata_bulk_dom_cli.py",
    )

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
        text = re.sub(
            r"MNTrapTeam \d+\.\d+\.\d+",
            f"MNTrapTeam {VERSION}",
            text,
            count=1,
        )
        gui.write_text(text, encoding="utf-8")

    installed = (pkg / "myata_bulk_dom_cli.py").read_text(encoding="utf-8-sig")
    if "falling back to Search/Buddies" not in installed:
        raise RuntimeError("v4.3.2 verification failed: self fallback missing")

    print("MNTrapTeam 4.3.2 applied.")
    print("Logged-in My Scores failures now fall back to Search/Buddies.")


if __name__ == "__main__":
    main()
