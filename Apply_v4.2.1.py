from pathlib import Path
import shutil
import subprocess
import sys

VERSION = "4.2.1"
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
        found = False
        for index, line in enumerate(lines):
            if line.strip().startswith("__version__"):
                lines[index] = f'__version__ = "{VERSION}"'
                found = True
                break
        if not found:
            lines.append(f'__version__ = "{VERSION}"')
        init.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Verify backward-compatible dashboard helper is present.
    dashboard_text = (pkg / "live_dashboard.py").read_text(encoding="utf-8")
    if "def _hoa_from_disciplines(" not in dashboard_text:
        raise RuntimeError(
            "v4.2.1 verification failed: _hoa_from_disciplines missing"
        )

    # Verify argparse really exposes --ata-file in the installed module.
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "mntrapteam.myata_bulk_dom_cli",
            "--help",
        ],
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "v4.2.1 verification failed while checking MyATA CLI:\n"
            + result.stderr
        )
    if "--ata-file" not in result.stdout:
        raise RuntimeError(
            "v4.2.1 verification failed: installed MyATA CLI "
            "does not expose --ata-file"
        )

    print("MNTrapTeam 4.2.1 applied.")
    print("Compatibility helper restored for existing live-dashboard tests.")
    print("Verified: MyATA CLI exposes --ata-file.")


if __name__ == "__main__":
    main()
