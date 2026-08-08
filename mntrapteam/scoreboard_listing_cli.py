from __future__ import annotations

import argparse

from .scoreboard_listing import discover_zone_shoots


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Discover Minnesota Zone shoots from ShootScoreBoard's own year listing"
    )
    parser.add_argument("--year", type=int, default=2026)
    args = parser.parse_args()

    print(
        f"Reading ShootScoreBoard's {args.year} shoot listing "
        "(one listing request, not an ID scan)..."
    )

    shoots = discover_zone_shoots(args.year)

    if not shoots:
        print("No Minnesota Zone shoots were matched.")
        return 1

    for shoot in shoots:
        print(
            f"{shoot.zone}: shootid={shoot.shoot_id} | "
            f"{shoot.text}"
        )

    missing = {
        "SOUTHERN", "CENTRAL", "NORTHERN"
    } - {shoot.zone for shoot in shoots}

    if missing:
        print()
        print("Still missing:", ", ".join(sorted(missing)))
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
