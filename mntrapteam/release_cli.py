from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

from mntrapteam.release_tools import (
    obsolete_upgrade_files,
    print_report,
    project_version,
    release_checks,
    write_report,
)


def clean_obsolete(root: Path, dry_run: bool) -> int:
    files = obsolete_upgrade_files(root)
    if not files:
        print("No obsolete patch files found.")
        return 0

    for path in files:
        print(("Would remove" if dry_run else "Removing") + f": {path}")
        if not dry_run:
            path.unlink()
    return 0


def create_tag(root: Path, push: bool) -> int:
    checks = release_checks(root, include_tests=True)
    if not print_report(checks):
        print("\nRelease checks failed. No tag was created.")
        return 1

    version = project_version(root)
    tag = f"v{version}"
    result = subprocess.run(
        ["git", "tag", "-a", tag, "-m", f"MNTrapTeam {version}"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        print(result.stderr)
        return result.returncode

    print(f"Created tag {tag}.")
    if push:
        pushed = subprocess.run(
            ["git", "push", "origin", tag],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
        print(pushed.stdout or pushed.stderr)
        return pushed.returncode

    print(f"To publish it later: git push origin {tag}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="MNTrapTeam release helper")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="Run release checks")
    check.add_argument("--skip-tests", action="store_true")
    check.add_argument("--json", default="release-check.json")

    clean = sub.add_parser("clean", help="Remove obsolete patch files")
    clean.add_argument("--dry-run", action="store_true")

    tag = sub.add_parser("tag", help="Create an annotated Git tag")
    tag.add_argument("--push", action="store_true")

    args = parser.parse_args()
    root = Path(".").resolve()

    if args.command == "check":
        checks = release_checks(root, include_tests=not args.skip_tests)
        write_report(checks, root / args.json)
        return 0 if print_report(checks) else 1
    if args.command == "clean":
        return clean_obsolete(root, args.dry_run)
    if args.command == "tag":
        return create_tag(root, args.push)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
