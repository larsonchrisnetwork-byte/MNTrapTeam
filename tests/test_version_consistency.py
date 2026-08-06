from pathlib import Path
import re


def test_version_files_are_consistent():
    version = Path("VERSION").read_text(encoding="utf-8").strip()
    assert re.fullmatch(r"\d+\.\d+\.\d+", version)

    gui = Path("mntrapteam/gui.py").read_text(encoding="utf-8")
    assert f"MNTrapTeam {version}" in gui

    init_file = Path("mntrapteam/__init__.py")
    if init_file.exists():
        package = init_file.read_text(encoding="utf-8")
        match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', package)
        if match:
            assert match.group(1) == version
