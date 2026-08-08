from __future__ import annotations

import argparse

from .sos_discovery import capture_sos_discovery


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture SOS Clays routes/API calls for Minnesota shoot importer development"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run without a visible browser (not recommended for first capture)",
    )
    args = parser.parse_args()

    result = capture_sos_discovery(
        headed=not args.headless,
    )

    print()
    print("SOS discovery capture complete.")
    print(f"Capture directory: {result.capture_directory}")
    print(f"Pages captured: {result.pages_visited}")
    print(f"JSON responses captured: {result.json_responses}")
    print(f"Unique candidate URLs: {result.candidate_urls}")
    print()
    print("Next, run:")
    print(
        'Get-Content "'
        + result.capture_directory
        + '\\summary.json" -Raw'
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
