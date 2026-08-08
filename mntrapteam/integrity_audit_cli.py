from __future__ import annotations

from collections import defaultdict

from .database import Database
from .identity import normalize_ata, normalize_person_name
from .paths import DATA


def _rows(db, sql, params=()):
    return [dict(r) for r in db.query(sql, params)]


def _table_exists(db, table):
    rows = _rows(
        db,
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND name=?
        """,
        (table,),
    )
    return bool(rows)


def main() -> int:
    db = Database(DATA / "mntrapteam.db")

    print("MNTrapTeam v4.1 Shooter Integrity Audit")
    print("=======================================")
    print()

    shooters = _rows(
        db,
        """
        SELECT id, ata_number, first_name, last_name, display_name,
               state, category, active
        FROM shooters
        ORDER BY id
        """,
    )

    print(f"Shooter records: {len(shooters)}")
    print()

    # 1) Duplicate ATA numbers.
    by_ata = defaultdict(list)
    for shooter in shooters:
        ata = normalize_ata(shooter.get("ata_number"))
        if ata:
            by_ata[ata].append(shooter)

    dup_atas = {
        ata: rows
        for ata, rows in by_ata.items()
        if len(rows) > 1
    }

    print("DUPLICATE ATA NUMBERS")
    print("---------------------")
    if not dup_atas:
        print("None")
    else:
        for ata, rows in sorted(dup_atas.items()):
            print(f"ATA {ata}")
            for row in rows:
                print(
                    f"  id={row['id']} | {row['display_name']} | "
                    f"state={row.get('state')} | category={row.get('category')}"
                )
    print()

    # 2) Same normalized name, including blank-ATA placeholders.
    by_name = defaultdict(list)
    for shooter in shooters:
        key = normalize_person_name(shooter.get("display_name"))
        if key:
            by_name[key].append(shooter)

    name_groups = {
        name: rows
        for name, rows in by_name.items()
        if len(rows) > 1
    }

    print("SAME NORMALIZED NAME / MULTIPLE SHOOTER ROWS")
    print("--------------------------------------------")
    if not name_groups:
        print("None")
    else:
        for name, rows in sorted(name_groups.items()):
            print(name)
            for row in rows:
                print(
                    f"  id={row['id']} | ATA {normalize_ata(row.get('ata_number')) or 'blank'} | "
                    f"{row['display_name']}"
                )
    print()

    # 3) Blank ATA rows.
    blank_ata = [
        row for row in shooters
        if not normalize_ata(row.get("ata_number"))
    ]

    print("BLANK-ATA SHOOTER ROWS")
    print("----------------------")
    if not blank_ata:
        print("None")
    else:
        for row in blank_ata:
            print(
                f"id={row['id']} | {row['display_name']} | "
                f"state={row.get('state')} | category={row.get('category')}"
            )
    print()

    # 4) 2026 season_stats coverage for ATA-numbered shooters.
    ata_shooters = [
        row for row in shooters
        if normalize_ata(row.get("ata_number"))
    ]

    missing_stats = []
    multiple_stats = []

    for shooter in ata_shooters:
        stat_rows = _rows(
            db,
            """
            SELECT id, season, source
            FROM season_stats
            WHERE shooter_id=? AND season=2026
            ORDER BY id
            """,
            (shooter["id"],),
        )

        if not stat_rows:
            missing_stats.append(shooter)
        elif len(stat_rows) > 1:
            multiple_stats.append((shooter, stat_rows))

    print("ATA-NUMBERED SHOOTERS MISSING 2026 SEASON_STATS")
    print("-----------------------------------------------")
    if not missing_stats:
        print("None")
    else:
        for row in missing_stats:
            print(
                f"{normalize_ata(row.get('ata_number'))} | "
                f"id={row['id']} | {row['display_name']}"
            )
    print()

    print("MULTIPLE 2026 SEASON_STATS ROWS")
    print("-------------------------------")
    if not multiple_stats:
        print("None")
    else:
        for shooter, stats in multiple_stats:
            print(
                f"{normalize_ata(shooter.get('ata_number'))} | "
                f"id={shooter['id']} | {shooter['display_name']}"
            )
            for stat in stats:
                print(
                    f"  season_stats id={stat['id']} | source={stat.get('source')}"
                )
    print()

    # 5) HAA records that reference missing shooters.
    print("ORPHANED HAA REFERENCES")
    print("-----------------------")

    orphan_count = 0

    if _table_exists(db, "haa_qualifications"):
        rows = _rows(
            db,
            """
            SELECT h.rowid AS rid, h.shooter_id, h.season
            FROM haa_qualifications h
            LEFT JOIN shooters s ON s.id=h.shooter_id
            WHERE s.id IS NULL
            ORDER BY h.rowid
            """,
        )
        for row in rows:
            print(
                f"haa_qualifications row={row['rid']} | "
                f"shooter_id={row['shooter_id']} | season={row['season']}"
            )
        orphan_count += len(rows)

    if _table_exists(db, "zone_haa_qualifications"):
        rows = _rows(
            db,
            """
            SELECT z.rowid AS rid, z.shooter_id, z.season, z.zone
            FROM zone_haa_qualifications z
            LEFT JOIN shooters s ON s.id=z.shooter_id
            WHERE s.id IS NULL
            ORDER BY z.rowid
            """,
        )
        for row in rows:
            print(
                f"zone_haa row={row['rid']} | "
                f"shooter_id={row['shooter_id']} | "
                f"season={row['season']} | zone={row['zone']}"
            )
        orphan_count += len(rows)

    if orphan_count == 0:
        print("None")
    print()

    # 6) HAA-qualified ATA shooters with no 2026 stats.
    haa_no_stats = []

    for shooter in ata_shooters:
        shooter_id = int(shooter["id"])

        state_haa = 0
        zone_haa = 0

        if _table_exists(db, "haa_qualifications"):
            rows = _rows(
                db,
                """
                SELECT COUNT(*) AS n
                FROM haa_qualifications
                WHERE shooter_id=? AND season=2026 AND verified=1
                """,
                (shooter_id,),
            )
            state_haa = int(rows[0]["n"] or 0) if rows else 0

        if _table_exists(db, "zone_haa_qualifications"):
            rows = _rows(
                db,
                """
                SELECT COUNT(*) AS n
                FROM zone_haa_qualifications
                WHERE shooter_id=? AND season=2026 AND verified=1
                """,
                (shooter_id,),
            )
            zone_haa = int(rows[0]["n"] or 0) if rows else 0

        if not (state_haa or zone_haa):
            continue

        stats = _rows(
            db,
            """
            SELECT id
            FROM season_stats
            WHERE shooter_id=? AND season=2026
            LIMIT 1
            """,
            (shooter_id,),
        )

        if not stats:
            haa_no_stats.append(
                (
                    shooter,
                    "State+Zone" if state_haa and zone_haa
                    else "State" if state_haa
                    else "Zone",
                )
            )

    print("HAA-QUALIFIED SHOOTERS WITH NO 2026 SEASON_STATS")
    print("------------------------------------------------")
    if not haa_no_stats:
        print("None")
    else:
        for shooter, source in haa_no_stats:
            print(
                f"{normalize_ata(shooter.get('ata_number'))} | "
                f"{shooter['display_name']} | HAA={source}"
            )
    print()

    # 7) Summary / repair priorities.
    print("SUMMARY")
    print("-------")
    print(f"Duplicate ATA groups: {len(dup_atas)}")
    print(f"Same-name multi-row groups: {len(name_groups)}")
    print(f"Blank-ATA shooter rows: {len(blank_ata)}")
    print(f"ATA shooters missing 2026 season_stats: {len(missing_stats)}")
    print(f"Shooters with multiple 2026 season_stats rows: {len(multiple_stats)}")
    print(f"Orphaned HAA references: {orphan_count}")
    print(f"HAA-qualified shooters missing 2026 season_stats: {len(haa_no_stats)}")
    print()

    print("RECOMMENDED REPAIR ORDER")
    print("------------------------")
    print("1. Resolve duplicate/same-name identity rows.")
    print("2. Fill missing 2026 MyATA season_stats for HAA-qualified shooters.")
    print("3. Re-run this audit until identity/orphan counts are clean.")
    print("4. Then wire v4 eligibility into Live Team.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
