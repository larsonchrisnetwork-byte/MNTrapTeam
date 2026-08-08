from __future__ import annotations

from dataclasses import dataclass
import re

from .haa_gate import HAARecord, rebuild_season_haa_flags, save_record
from .matcher import ShooterMatcher
from .shootscoreboard_web import fetch_text, import_public_shoot, load_public_shoot
from .zone_residency import get_resident_zone


ZONE_HOSTS = {
    "NORTHERN": ("GRAND RAPIDS", "NORTHERN ZONE"),
    "CENTRAL": ("BEAVERBROOK", "CENTRAL ZONE"),
    "SOUTHERN": ("LESTER PRAIRIE", "SOUTHERN ZONE"),
}


@dataclass
class ZoneShootCandidate:
    shoot_id: int
    zone: str
    name: str
    start_date: str
    end_date: str


@dataclass
class ZoneHAASyncResult:
    shoot_id: int
    zone: str
    shoot_name: str
    imported_score_rows: int
    haa_completers: int
    qualified_resident_zone: int
    resident_zone_unverified: int
    wrong_resident_zone: int
    warnings: list[str]


def _zone_from_name(name):
    upper = " ".join(str(name or "").upper().split())
    for zone, hints in ZONE_HOSTS.items():
        if any(hint in upper for hint in hints):
            return zone
    return ""


def _category(value):
    upper = str(value or "").strip().upper()
    aliases = {
        "": "MEN",
        "JR": "JUNIOR",
        "JRG": "JUNIOR_GOLD",
        "SJ": "SUB_JR",
        "SUBJ": "SUB_JR",
        "SUBV": "SUB_VET",
        "VT": "VET",
        "SRVT": "SR_VET",
        "LD1": "LADY_I",
        "LD2": "LADY_II",
        "LDC": "LADY_I",
    }
    return aliases.get(upper, upper or "MEN")


def _name_key(value):
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def discover_2026_zone_shoots(start_id=2000, end_id=2100, *, fetcher=fetch_text):
    found = {}
    for shoot_id in range(int(start_id), int(end_id) + 1):
        if len(found) == 3:
            break
        try:
            shoot = load_public_shoot(shoot_id, fetcher=fetcher)
        except Exception:
            continue
        if not shoot.start_date.startswith("2026-06"):
            continue
        zone = _zone_from_name(shoot.name)
        if not zone:
            continue
        found[zone] = ZoneShootCandidate(
            shoot_id=shoot.shoot_id,
            zone=zone,
            name=shoot.name,
            start_date=shoot.start_date,
            end_date=shoot.end_date,
        )
    return [found[z] for z in ("SOUTHERN", "CENTRAL", "NORTHERN") if z in found]


def _shooter_id(database, matcher, name):
    shooter_id, _confidence = matcher.match(name, "")
    if shooter_id is not None:
        return int(shooter_id)
    rows = database.query("SELECT id,display_name FROM shooters")
    matches = [row for row in rows if _name_key(row["display_name"]) == _name_key(name)]
    return int(matches[0]["id"]) if len(matches) == 1 else None


def zone_haa_completers(database, shoot, season):
    matcher = ShooterMatcher(database, 88)
    totals = {}

    for event in shoot.events:
        if event.discipline not in {"singles", "handicap", "doubles"}:
            continue
        for entry in event.entries:
            if str(entry.get("state") or "").upper() != "MN":
                continue
            shooter_id = _shooter_id(database, matcher, entry["name"])
            if shooter_id is None:
                continue
            item = totals.setdefault(
                shooter_id,
                {
                    "shooter_id": shooter_id,
                    "name": entry["name"],
                    "category": _category(entry.get("category") or ""),
                    "singles": 0,
                    "handicap": 0,
                    "doubles": 0,
                },
            )
            item[event.discipline] += int(entry.get("targets") or 0)
            if entry.get("category"):
                item["category"] = _category(entry["category"])

    completers = []
    for item in totals.values():
        is_sub_jr = item["category"] in {"SUB_JR", "SUB_JUNIOR"}
        complete = (
            item["singles"] >= 200
            and item["handicap"] >= 100
            and (is_sub_jr or item["doubles"] >= 100)
        )
        if complete:
            completers.append(item)
    return completers


def sync_zone_haa(database, shoot_id, zone, season=2026):
    zone = zone.upper()
    shoot = load_public_shoot(shoot_id)

    imported = import_public_shoot(
        database,
        shoot,
        season,
        mn_only=True,
        club=shoot.name,
        matcher_threshold=88,
    )

    completers = zone_haa_completers(database, shoot, season)
    qualified = 0
    unverified = 0
    wrong_zone = 0
    warnings = list(imported.warnings)

    for item in completers:
        resident = get_resident_zone(database, item["shooter_id"], season)
        resident_zone = resident["resident_zone"]
        resident_verified = bool(resident["verified"])

        if resident_verified and resident_zone == zone:
            qualified += 1
        elif resident_verified and resident_zone and resident_zone != zone:
            wrong_zone += 1
        else:
            unverified += 1

        save_record(
            database,
            HAARecord(
                season=season,
                shooter_id=item["shooter_id"],
                route="ZONE",
                shoot_name=shoot.name,
                shoot_date=shoot.end_date,
                shoot_zone=zone,
                resident_zone=resident_zone,
                category=item["category"],
                singles_completed=item["singles"] >= 200,
                handicap_completed=item["handicap"] >= 100,
                doubles_completed=item["doubles"] >= 100,
                source_url=shoot.source_url,
                source_label="ShootScoreBoard live Zone HAA",
                source_coverage="COMPLETE",
                verified=resident_verified,
                notes=(
                    "Completed Zone HAA targets. "
                    + (
                        f"Verified resident zone {resident_zone}."
                        if resident_verified
                        else "Resident Minnesota zone not yet verified."
                    )
                ),
            ),
        )

    rebuild_season_haa_flags(database, season)

    return ZoneHAASyncResult(
        shoot_id=shoot.shoot_id,
        zone=zone,
        shoot_name=shoot.name,
        imported_score_rows=imported.score_rows_imported,
        haa_completers=len(completers),
        qualified_resident_zone=qualified,
        resident_zone_unverified=unverified,
        wrong_resident_zone=wrong_zone,
        warnings=warnings,
    )


def pending_zone_residency(database, season=2026):
    rows = database.query(
        '''
        SELECT
            h.shooter_id,
            s.ata_number,
            s.display_name,
            h.shoot_zone,
            h.shoot_name,
            h.shoot_date,
            h.category
        FROM haa_qualifications h
        JOIN shooters s ON s.id=h.shooter_id
        WHERE h.season=?
          AND h.route='ZONE'
          AND h.verified=0
          AND h.singles_completed=1
          AND h.handicap_completed=1
          AND (
                h.doubles_completed=1
                OR upper(h.category) IN ('SUB_JR','SUB_JUNIOR','SUBJUNIOR')
              )
        ORDER BY h.shoot_zone,s.display_name
        ''',
        (season,),
    )
    return [dict(row) for row in rows]
