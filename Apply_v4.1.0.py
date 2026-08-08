from pathlib import Path
import re
import shutil

VERSION = "4.1.0"
ROOT = Path(".")
SOURCE_ROOT = Path(__file__).resolve().parent


def copy_if_needed(src: Path, dst: Path):
    if src.resolve() == dst.resolve():
        print(f"Skipping self-copy: {dst}")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def main():
    target_pkg = ROOT / "mntrapteam"
    if not target_pkg.exists():
        raise SystemExit("Run from H:\\MNTrapTeam\\MNTrapTeam")

    copy_if_needed(
        SOURCE_ROOT / "mntrapteam" / "integrity_audit_cli.py",
        target_pkg / "integrity_audit_cli.py",
    )

    Path("VERSION").write_text(VERSION + "\n", encoding="utf-8")

    gui = target_pkg / "gui.py"
    if gui.exists():
        text = gui.read_text(encoding="utf-8")
        text = re.sub(
            r"MNTrapTeam \d+\.\d+\.\d+",
            f"MNTrapTeam {VERSION}",
            text,
            count=1,
        )
        gui.write_text(text, encoding="utf-8")

    init = target_pkg / "__init__.py"
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
        "MNTrapTeam 4.1.0 applied: Shooter Integrity Audit added."
    )


if __name__ == "__main__":
    main()
