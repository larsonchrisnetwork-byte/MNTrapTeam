from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json
import re
import subprocess
import sys
from typing import Iterable


SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


@dataclass
class Check:
    name: str
    passed: bool
    detail: str


def project_version(root: Path = Path(".")) -> str:
    version_file = root / "VERSION"
    if not version_file.exists():
        raise FileNotFoundError("VERSION file is missing")
    version = version_file.read_text(encoding="utf-8").strip()
    if not SEMVER.fullmatch(version):
        raise ValueError(f"VERSION is not valid semantic versioning: {version!r}")
    return version


def gui_version(root: Path = Path(".")) -> str | None:
    gui = root / "mntrapteam" / "gui.py"
    if not gui.exists():
        return None
    text = gui.read_text(encoding="utf-8")
    match = re.search(r"MNTrapTeam\s+(\d+\.\d+\.\d+)", text)
    return match.group(1) if match else None


def package_version(root: Path = Path(".")) -> str | None:
    init_file = root / "mntrapteam" / "__init__.py"
    if not init_file.exists():
        return None
    text = init_file.read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', text)
    return match.group(1) if match else None


def obsolete_upgrade_files(root: Path = Path(".")) -> list[Path]:
    patterns = (
        "Apply_v1.*.py",
        "Apply_v1.*.ps1",
        "Apply_v2.*.py",
        "Apply_v2.*.ps1",
        "README_UPGRADE.md",
        "README_V2_*_UPGRADE.md",
        "Flatten_Current_Repository.ps1",
    )
    found: set[Path] = set()
    for pattern in patterns:
        found.update(root.glob(pattern))
    # Keep the current release application script if a user is checking before commit.
    current = project_version(root)
    found = {
        path
        for path in found
        if path.name not in {
            f"Apply_v{current}.py",
            f"Apply_v{current}.ps1",
        }
    }
    return sorted(found)


def git_output(args: list[str], root: Path = Path(".")) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )


def run_tests(root: Path = Path(".")) -> Check:
    python = root / ".venv" / "Scripts" / "python.exe"
    executable = str(python) if python.exists() else sys.executable
    result = subprocess.run(
        [executable, "-m", "pytest", "-q", "tests"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    output = (result.stdout + "\n" + result.stderr).strip()
    return Check("Tests", result.returncode == 0, output)


def release_checks(
    root: Path = Path("."),
    include_tests: bool = True,
) -> list[Check]:
    checks: list[Check] = []

    try:
        version = project_version(root)
        checks.append(Check("VERSION", True, version))
    except Exception as exc:
        checks.append(Check("VERSION", False, str(exc)))
        return checks

    displayed = gui_version(root)
    checks.append(
        Check(
            "GUI version",
            displayed == version,
            f"VERSION={version}; GUI={displayed or 'not found'}",
        )
    )

    package = package_version(root)
    checks.append(
        Check(
            "Package version",
            package in (None, version),
            (
                "No __version__ declared"
                if package is None
                else f"VERSION={version}; package={package}"
            ),
        )
    )

    status = git_output(["status", "--porcelain"], root)
    checks.append(
        Check(
            "Git available",
            status.returncode == 0,
            status.stderr.strip() or "Git repository detected",
        )
    )

    if status.returncode == 0:
        checks.append(
            Check(
                "Working tree",
                not bool(status.stdout.strip()),
                status.stdout.strip() or "Clean",
            )
        )

        remote = git_output(["remote", "-v"], root)
        checks.append(
            Check(
                "Git remote",
                remote.returncode == 0 and bool(remote.stdout.strip()),
                remote.stdout.strip() or remote.stderr.strip() or "No remote",
            )
        )

        tag = git_output(["tag", "--list", f"v{version}"], root)
        checks.append(
            Check(
                "Release tag unused",
                not bool(tag.stdout.strip()),
                (
                    f"v{version} is available"
                    if not tag.stdout.strip()
                    else f"v{version} already exists"
                ),
            )
        )

    obsolete = obsolete_upgrade_files(root)
    checks.append(
        Check(
            "Obsolete patch files",
            len(obsolete) == 0,
            (
                "None"
                if not obsolete
                else "\n".join(str(path) for path in obsolete)
            ),
        )
    )

    if include_tests:
        checks.append(run_tests(root))

    return checks


def write_report(checks: Iterable[Check], path: Path) -> None:
    payload = {
        "passed": all(check.passed for check in checks),
        "checks": [asdict(check) for check in checks],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def print_report(checks: Iterable[Check]) -> bool:
    all_passed = True
    for check in checks:
        mark = "PASS" if check.passed else "FAIL"
        print(f"[{mark}] {check.name}")
        if check.detail:
            for line in check.detail.splitlines():
                print(f"       {line}")
        all_passed = all_passed and check.passed
    return all_passed
