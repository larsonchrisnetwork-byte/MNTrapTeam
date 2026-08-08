from __future__ import annotations

import argparse

from .database import Database
from .paths import DATA
from .recent_score_scout_cli import (
    _event_date,
    _load_shoot_from_entries,
    _stored_event_name,
)


def _shooter(db: Database, ata: str):
    ata = "".join(ch for ch in str(ata) if ch.isdigit())
    rows = db.query(
        """
        SELECT id,ata_number,display_name
        FROM shooters
        WHERE ata_number=?
        """,
        (ata,),
    )
    if len(rows) != 1:
        raise RuntimeError(
            f"ATA {ata}: expected one shooter record, found {len(rows)}"
        )
    return rows[0]


def _ensure_shoot(db: Database, shoot) -> int:
    rows = db.query(
        """
        SELECT id FROM shoots
        WHERE source_url=? OR (name=? AND start_date=?)
        ORDER BY id LIMIT 1
        """,
        (shoot.source_url, shoot.name, shoot.start_date),
    )
    if rows:
        return int(rows[0]["id"])

    return int(
        db.execute(
            """
            INSERT INTO shoots(
                name,club,city,state,start_date,end_date,source_type,source_url
            ) VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                shoot.name,
                shoot.name,
                "",
                "",
                shoot.start_date,
                shoot.end_date,
                "Manual provisional",
                shoot.source_url,
            ),
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Add one controlled manual provisional score."
    )
    parser.add_argument("--ata", required=True)
    parser.add_argument("--shoot-id", type=int, required=True)
    parser.add_argument("--event-id", type=int, required=True)
    parser.add_argument(
        "--discipline",
        choices=("singles", "handicap", "doubles"),
        required=True,
    )
    parser.add_argument("--hits", type=int, required=True)
    parser.add_argument("--targets", type=int, default=100)
    parser.add_argument(
        "--in-state",
        action="store_true",
        help="Count this score toward Minnesota target requirements.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Actually insert. Without --write this is preview only.",
    )
    args = parser.parse_args()

    if args.targets <= 0 or args.hits < 0 or args.hits > args.targets:
        raise RuntimeError("Invalid hits/targets")

    db = Database(DATA / "mntrapteam.db")
    shooter = _shooter(db, args.ata)
    shoot = _load_shoot_from_entries(args.shoot_id, timeout=8)

    event = next(
        (
            e for e in shoot.events
            if int(e.event_id) == args.event_id
            and e.discipline == args.discipline
        ),
        None,
    )
    if event is None:
        raise RuntimeError(
            f"Shoot {args.shoot_id}: E{args.event_id} "
            f"{args.discipline} was not found"
        )

    event_date = _event_date(shoot, event)
    event_name = _stored_event_name(event)

    existing = db.query(
        """
        SELECT sc.id,sc.source,sc.hits,sc.targets
        FROM scores sc
        LEFT JOIN shoots sh ON sh.id=sc.shoot_id
        WHERE sc.shooter_id=?
          AND (sh.source_url=? OR (sh.name=? AND sh.start_date=?))
          AND upper(sc.event_name)=upper(?)
          AND lower(sc.discipline)=lower(?)
        """,
        (
            int(shooter["id"]),
            shoot.source_url,
            shoot.name,
            shoot.start_date,
            event_name,
            args.discipline,
        ),
    )

    print("MNTrapTeam Manual Provisional Score")
    print("===================================")
    print(f"Shooter: {shooter['display_name']} | ATA {shooter['ata_number']}")
    print(f"Shoot: {shoot.name} | shootid {args.shoot_id}")
    print(f"Event: {event_name} | {event_date}")
    print(f"Score: {args.hits}/{args.targets} {args.discipline}")
    print(f"Minnesota target credit: {'YES' if args.in_state else 'NO'}")

    if existing:
        print()
        print("NOT INSERTED: a score already exists for this shooter/event.")
        for row in existing:
            print(
                f"  id={row['id']} | {row['source']} | "
                f"{row['hits']}/{row['targets']}"
            )
        return 2

    if not args.write:
        print()
        print("PREVIEW ONLY — add --write to insert this provisional score.")
        return 0

    local_shoot_id = _ensure_shoot(db, shoot)
    db.execute(
        """
        INSERT INTO scores(
            shooter_id,shoot_id,event_date,event_name,discipline,
            targets,hits,in_state,club_key,source,official,raw_name
        ) VALUES(?,?,?,?,?,?,?,?,?,?,0,?)
        """,
        (
            int(shooter["id"]),
            local_shoot_id,
            event_date,
            event_name,
            args.discipline,
            args.targets,
            args.hits,
            1 if args.in_state else 0,
            shoot.name,
            "Manual provisional",
            shooter["display_name"],
        ),
    )

    print()
    print("Manual provisional score inserted.")
    print("Official MyATA baseline was not modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
