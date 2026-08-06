from __future__ import annotations

import argparse
from dataclasses import asdict
import json

from .connectors import (
    PROVIDERS,
    SessionStore,
    check_session,
    connect_interactively,
    status_rows,
)
from .paths import DATA


def print_status(row):
    value = row.likely_authenticated
    auth = "YES" if value is True else ("NO" if value is False else "UNKNOWN")
    print(f"{row.display_name}:")
    print(f"  Profile: {row.profile_path}")
    print(f"  Profile exists: {row.profile_exists}")
    print(f"  Likely authenticated: {auth}")
    print(f"  Last checked: {row.last_checked or 'Never'}")
    print(f"  Last URL: {row.last_url or 'None'}")
    print(f"  Detail: {row.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Manage secure MNTrapTeam browser sessions"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    connect = sub.add_parser("connect", help="Open provider login interactively")
    connect.add_argument("provider", choices=sorted(PROVIDERS))
    connect.add_argument("--url")

    check = sub.add_parser("check", help="Check a saved session")
    check.add_argument("provider", choices=sorted(PROVIDERS))

    status = sub.add_parser("status", help="Show all session statuses")
    status.add_argument("--json", action="store_true")

    clear = sub.add_parser("clear", help="Delete a saved provider session")
    clear.add_argument("provider", choices=sorted(PROVIDERS))

    args = parser.parse_args()
    store = SessionStore(DATA)

    if args.command == "connect":
        row = connect_interactively(DATA, args.provider, start_url=args.url)
        print_status(row)
        return 0

    if args.command == "check":
        row = check_session(DATA, args.provider)
        print_status(row)
        return 0 if row.likely_authenticated is not False else 1

    if args.command == "status":
        rows = status_rows(DATA)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            for row in rows:
                value = row["likely_authenticated"]
                auth = "YES" if value is True else ("NO" if value is False else "UNKNOWN")
                print(
                    f"{row['display_name']}: {auth} "
                    f"({row['detail']})"
                )
        return 0

    removed = store.clear(args.provider)
    print("Session removed." if removed else "No saved session existed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
