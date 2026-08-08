from __future__ import annotations

import re
from typing import Any

from .haa_gate import haa_status
from .reconciliation import SOURCE_PRIORITY
from .live_display import actionable_missing_requirements
from .official_baseline import ensure_schema as ensure_baseline_schema, get_baseline

DISCIPLINES = ("singles", "handicap", "doubles")


def _season_values(row: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result = {}
    for discipline in DISCIPLINES:
        targets = int(row.get(f"{discipline}_targets") or 0)
        hits = int(row.get(f"{discipline}_hits") or 0)
        result[discipline] = {
            "targets": targets,
            "hits": hits,
            "average": (hits / targets * 100.0) if targets else 0.0,
        }
    return result


def _hoa_from_disciplines(values: dict[str, dict[str, Any]]) -> float:
    """Backward-compatible HOA helper used by the existing test suite."""
    averages = [
        float(values[discipline]["average"])
        for discipline in DISCIPLINES
        if int(values[discipline].get("targets") or 0) > 0
    ]
    return sum(averages) / len(averages) if averages else 0.0


def _hoa(values: dict[str, dict[str, Any]]) -> float:
    return _hoa_from_disciplines(values)


def _provisional_source_key(value: Any) -> str:
    text = str(value or "").strip().lower()
    if "myata" in text:
        return "myata"
    if "shootscoreboard" in text:
        return "shootscoreboard"
    if "sos" in text and "clay" in text:
        return "sosclays"
    if text.startswith("ata ") or "shootata" in text:
        return "ata_scores"
    return "manual"


def _provisional_event_key(row: dict[str, Any]) -> tuple:
    event_name = str(row.get("event_name") or "").strip()
    match = re.search(r"\b(?:EVENT|E)\s*#?\s*(\d+)\b", event_name, re.IGNORECASE)
    if match:
        event_slot = f"E{int(match.group(1))}"
    else:
        event_slot = re.sub(r"[^A-Z0-9]+", " ", event_name.upper()).strip()
        if not event_slot:
            club = re.sub(
                r"[^A-Z0-9]+",
                " ",
                str(row.get("club_key") or "").upper(),
            ).strip()
            event_slot = f"CLUB:{club}"

    return (
        str(row.get("event_date") or ""),
        str(row.get("discipline") or "").lower(),
        event_slot,
        int(row.get("targets") or 0),
    )


def _provisional_after_baseline(database, shooter_id: int, through_date: str):
    empty = {
        "rows": [],
        "disciplines": {d: {"targets": 0, "hits": 0} for d in DISCIPLINES},
        "mn": {d: 0 for d in DISCIPLINES},
        "sources": [],
        "latest_date": "",
        "clubs": set(),
    }
    if not through_date:
        return empty

    rows = database.query(
        """
        SELECT id,event_date,event_name,discipline,targets,hits,
               in_state,club_key,source,official
        FROM scores
        WHERE shooter_id=?
          AND official=0
          AND event_date>?
        ORDER BY event_date,id
        """,
        (shooter_id, through_date),
    )

    selected = {}
    sources = set()

    for raw in rows:
        row = dict(raw)
        discipline = str(row.get("discipline") or "").lower()
        if discipline not in DISCIPLINES:
            continue

        source = str(row.get("source") or "").strip()
        if source:
            sources.add(source)

        key = _provisional_event_key(row)
        current = selected.get(key)

        candidate_priority = SOURCE_PRIORITY.get(
            _provisional_source_key(source),
            0,
        )
        current_priority = (
            SOURCE_PRIORITY.get(
                _provisional_source_key(current.get("source")),
                0,
            )
            if current
            else -1
        )

        if current is None or candidate_priority > current_priority:
            selected[key] = row

    selected_rows = sorted(
        selected.values(),
        key=lambda row: (
            str(row.get("event_date") or ""),
            int(row.get("id") or 0),
        ),
    )

    totals = {d: {"targets": 0, "hits": 0} for d in DISCIPLINES}
    mn = {d: 0 for d in DISCIPLINES}
    clubs = set()
    latest = ""

    for row in selected_rows:
        discipline = str(row.get("discipline") or "").lower()
        targets = int(row.get("targets") or 0)
        hits = int(row.get("hits") or 0)

        totals[discipline]["targets"] += targets
        totals[discipline]["hits"] += hits

        if int(row.get("in_state") or 0):
            mn[discipline] += targets
            club = str(row.get("club_key") or "").strip()
            if club:
                clubs.add(club.upper())

        latest = max(latest, str(row.get("event_date") or ""))

    return {
        "rows": selected_rows,
        "disciplines": totals,
        "mn": mn,
        "sources": sorted(sources),
        "latest_date": latest,
        "clubs": clubs,
    }


def _progress(team_service, row, haa_qualified, current_values, current_mn, current_clubs):
    req = team_service.rules.rules["teams"]["MEN"]
    general = team_service.rules.rules["general"]

    progress = {}
    for discipline in DISCIPLINES:
        progress[discipline] = (
            int(current_values[discipline]["targets"]),
            int(req[discipline]),
        )
        progress[f"mn_{discipline}"] = (
            int(current_mn[discipline]),
            int(general["in_state"][discipline]),
        )
    progress["clubs"] = (int(current_clubs), int(general["clubs"]))
    progress["haa"] = (1 if haa_qualified else 0, 1)

    missing = actionable_missing_requirements(progress)

    eligible = all(have >= need for have, need in progress.values())
    if str(row.get("state") or "MN").upper() != "MN":
        eligible = False
        missing = (
            "Not marked MN resident"
            if missing == "Ready ✓"
            else missing + "; Not marked MN resident"
        )
    return eligible, missing


def live_team_rows(database, team_service, season: int, team: str = "MEN"):
    rankings = team_service.rankings(season, team)
    ensure_baseline_schema(database)
    rows = []

    for ranking in rankings:
        shooter_id = int(ranking["id"])
        official_values = _season_values(ranking)
        official_hoa = _hoa(official_values)

        haa = haa_status(database, season, shooter_id)
        stats_haa_complete = bool(ranking.get("haa_complete"))
        haa_qualified = bool(haa.get("haa_qualified")) or stats_haa_complete

        # State Shoot is complete: HAA is the hard candidate-pool gate.
        # Do not track shooters outside that frozen pool in the State Team race.
        if not haa_qualified:
            continue

        baseline = get_baseline(database, shooter_id, season)
        official_through = str(baseline.get("official_through_date") or "")

        provisional = _provisional_after_baseline(
            database,
            shooter_id,
            official_through,
        )

        current_values = {}
        for discipline in DISCIPLINES:
            targets = (
                int(official_values[discipline]["targets"])
                + int(provisional["disciplines"][discipline]["targets"])
            )
            hits = (
                int(official_values[discipline]["hits"])
                + int(provisional["disciplines"][discipline]["hits"])
            )
            current_values[discipline] = {
                "targets": targets,
                "hits": hits,
                "average": (hits / targets * 100.0) if targets else 0.0,
            }

        current_hoa = _hoa(current_values)

        current_mn = {
            discipline: (
                int(ranking.get(f"mn_{discipline}_targets") or 0)
                + int(provisional["mn"][discipline])
            )
            for discipline in DISCIPLINES
        }

        # season_stats already contains the known official/enriched club count.
        # Add only new post-baseline MN clubs that are not already guaranteed to
        # be represented. This is intentionally conservative.
        current_clubs = int(ranking.get("mn_clubs") or 0)
        # Conservative live club handling: don't silently inflate a known
        # official/enriched club count from provisional observations.
        if current_clubs == 0 and provisional["clubs"]:
            current_clubs = len(provisional["clubs"])

        current_eligible, need_to_qualify = _progress(
            team_service,
            ranking,
            haa_qualified,
            current_values,
            current_mn,
            current_clubs,
        )

        pending_targets = sum(
            int(provisional["disciplines"][d]["targets"])
            for d in DISCIPLINES
        )

        row = dict(ranking)
        row.update(
            {
                "haa_qualified": haa_qualified,
                "haa_gate": "QUALIFIED" if haa_qualified else "NOT QUALIFIED",
                "haa_route": haa.get("haa_route") or (
                    "Verified season record" if stats_haa_complete else ""
                ),
                "official_hoa": official_hoa,
                "current_hoa": current_hoa,
                "live_hoa": current_hoa,
                "hoa_delta": current_hoa - official_hoa,
                "pending_targets": pending_targets,
                "official_through_date": official_through,
                "latest_provisional_date": provisional["latest_date"],
                "current_eligible": current_eligible,
                "eligible": current_eligible,
                "qualification_status": (
                    "QUALIFIED" if current_eligible else "NOT QUALIFIED"
                ),
                "need_to_qualify": need_to_qualify,
                "live_singles_targets": current_values["singles"]["targets"],
                "live_handicap_targets": current_values["handicap"]["targets"],
                "live_doubles_targets": current_values["doubles"]["targets"],
                "current_mn_singles": current_mn["singles"],
                "current_mn_handicap": current_mn["handicap"],
                "current_mn_doubles": current_mn["doubles"],
                "current_mn_clubs": current_clubs,
                "race_source": (
                    "MyATA official"
                    + (
                        " + " + ", ".join(provisional["sources"])
                        if provisional["sources"]
                        else ""
                    )
                ),
                "_eligibility_color": "green" if current_eligible else "red",
                "provisional_overlay_ready": bool(official_through),
                "baseline_status": (
                    f"Ready through {official_through}"
                    if official_through
                    else "Needs MyATA refresh"
                ),
            }
        )
        rows.append(row)

    # Everyone remains visible, including people who are not yet qualified.
    rows.sort(
        key=lambda row: (
            -float(row.get("current_hoa") or 0.0),
            str(row.get("display_name") or "").upper(),
        )
    )

    fully_qualified = [row for row in rows if row["current_eligible"]]
    team_size = int(team_service.rules.rules["teams"][team]["size"])
    selected = fully_qualified[:team_size]
    live_cut = (
        float(selected[-1]["current_hoa"])
        if len(selected) == team_size
        else None
    )

    qualified_rank = {
        int(row["id"]): rank
        for rank, row in enumerate(fully_qualified, 1)
    }

    for rank, row in enumerate(rows, 1):
        row["race_rank"] = rank
        row["qualified_rank"] = qualified_rank.get(int(row["id"]))
        row["live_pool_rank"] = rank
        row["live_team"] = row in selected
        row["live_cut_hoa"] = live_cut
        row["live_gap_to_cut"] = (
            float(row["current_hoa"]) - live_cut
            if live_cut is not None
            else None
        )

    return {
        "summary": {
            "team": team,
            "team_size": team_size,
            "tracked": len(rows),
            "haa_qualified": sum(bool(r["haa_qualified"]) for r in rows),
            "fully_qualified": len(fully_qualified),
            "eligible_qualified": len(fully_qualified),
            "selected": len(selected),
            "live_cut_hoa": live_cut,
            "pending_targets": sum(int(r["pending_targets"]) for r in rows),
            "provisional_shooters": sum(
                int(r["pending_targets"]) > 0 for r in rows
            ),
            "baseline_ready": sum(
                bool(r["provisional_overlay_ready"]) for r in rows
            ),
            "disputed_targets": 0,
            "observation_shooters": sum(
                int(r["pending_targets"]) > 0 for r in rows
            ),
        },
        "rows": rows,
    }


def live_dashboard_for_ata(
    database,
    team_service,
    season: int,
    ata_number: str,
    team: str = "MEN",
):
    ata = "".join(ch for ch in str(ata_number or "") if ch.isdigit())
    result = live_team_rows(database, team_service, season, team)
    shooter = next(
        (
            row
            for row in result["rows"]
            if "".join(
                ch for ch in str(row.get("ata_number") or "") if ch.isdigit()
            ) == ata
        ),
        None,
    )
    return {"summary": result["summary"], "shooter": shooter}
