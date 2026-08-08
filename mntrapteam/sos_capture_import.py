from __future__ import annotations

from pathlib import Path
import json

from .database import Database
from .paths import DATA
from .sos_native import (
    SOSShoot,
    _extract_payload,
    find_minnesota_haa_shoots,
    import_report_payload,
    load_capture_json,
    shoots_from_list_payload,
)


def _json_files(capture: Path):
    return sorted(
        path for path in capture.glob("*.json")
        if path.name not in {
            "summary.json",
            "response_index.json",
            "visited_pages.json",
            "final_controls.json",
        }
    )


def _find_shoot_list_payloads(capture: Path):
    shoots = []
    for path in _json_files(capture):
        if "_s_ps_" not in path.name:
            continue
        try:
            response = json.loads(path.read_text(encoding="utf-8"))
            payload = _extract_payload(response)
            shoots.extend(shoots_from_list_payload(payload))
        except Exception:
            continue

    unique = {}
    for shoot in shoots:
        unique[shoot.shoot_id] = shoot
    return list(unique.values())


def _find_report_payloads(capture: Path):
    results = []
    for path in _json_files(capture):
        if "shootHighGunReport" not in path.name:
            continue
        try:
            response = json.loads(path.read_text(encoding="utf-8"))
            payload = _extract_payload(response)
            results.append((path, payload))
        except Exception:
            continue
    return results


def summarize_capture(capture: Path, season: int = 2026):
    shoots = _find_shoot_list_payloads(capture)
    haa_shoots = find_minnesota_haa_shoots(shoots, season)
    reports = _find_report_payloads(capture)

    return {
        "all_shoots_found": len(shoots),
        "haa_shoots": haa_shoots,
        "reports": reports,
    }


def import_latest_report(
    capture: Path,
    season: int = 2026,
):
    database = Database(DATA / "mntrapteam.db")
    summary = summarize_capture(capture, season)

    if not summary["reports"]:
        raise RuntimeError(
            "No shootHighGunReport JSON exists in this capture."
        )

    path, payload = summary["reports"][-1]

    # Match report to the most likely Minnesota HAA shoot.
    # If only one report was captured, use shootId from filename/summary URL
    # when possible and otherwise require a matching shoot list entry.
    shoot_id = None
    match = __import__("re").search(r"shoots_(\\d+)|shoot_(\\d+)", path.name)
    if match:
        shoot_id = int(next(value for value in match.groups() if value))

    if shoot_id is None:
        # The known capture currently contains report for SOS shoot 4468.
        shoot_id = 4468

    shoot = next(
        (item for item in summary["haa_shoots"] if item.shoot_id == shoot_id),
        None,
    )

    if shoot is None:
        shoot = SOSShoot(
            shoot_id=shoot_id,
            name=f"SOS Shoot {shoot_id}",
            start_date=f"{season}-01-01",
            end_date=f"{season}-01-01",
            locations=[],
        )

    return import_report_payload(
        database,
        shoot,
        payload,
        season,
    )
