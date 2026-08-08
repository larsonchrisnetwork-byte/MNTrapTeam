from __future__ import annotations

import argparse
from pathlib import Path

from .paths import DATA
from .sos_capture_import import summarize_capture, import_latest_report


def latest_capture() -> Path:
    root = DATA / "connector_downloads" / "sos"
    candidates = sorted(
        (
            path for path in root.iterdir()
            if path.is_dir()
        ),
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError("No SOS captures found")
    return candidates[0]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect/import native SOS JSON capture"
    )
    parser.add_argument(
        "command",
        choices=["summary", "import-latest-report"],
    )
    parser.add_argument("--capture")
    parser.add_argument("--season", type=int, default=2026)
    args = parser.parse_args()

    capture = Path(args.capture) if args.capture else latest_capture()

    if args.command == "summary":
        result = summarize_capture(capture, args.season)
        print(f"Capture: {capture}")
        print(f"Unique shoots found in list responses: {result['all_shoots_found']}")
        print()
        print("Minnesota HAA shoots found:")
        for shoot in result["haa_shoots"]:
            print(
                f"  {shoot.shoot_id} | {shoot.start_date} | {shoot.name}"
            )
        print()
        print(f"High-gun report captures: {len(result['reports'])}")
        for path, _payload in result["reports"]:
            print(f"  {path.name}")
        return 0

    result = import_latest_report(capture, args.season)
    print(f"Shoot: {result.shoot_name}")
    print(f"Observations written: {result.observations_written}")
    print(f"Shooters created: {result.shooters_created}")
    print(f"HAA records written: {result.haa_records_written}")
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
