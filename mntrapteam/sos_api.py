from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Iterable
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json
import time

from .identity import normalize_ata
from .source_adapters import observe_event


API_BASE = "https://api-dot-sosclays-app.appspot.com/1"
FIREBASE_API_KEY = "AIzaSyBk3mdnlJi0RumInwmv2l7AaZsbWpIpCXQ"
FIREBASE_LOGIN = (
    "https://identitytoolkit.googleapis.com/v1/"
    "accounts:signInWithPassword"
)
FIREBASE_REFRESH = "https://securetoken.googleapis.com/v1/token"
EVENT_TYPES = {1: "singles", 2: "doubles", 3: "handicap"}


class SOSAPIError(RuntimeError):
    pass


@dataclass(frozen=True)
class SOSLocation:
    club_id: int
    club_name: str
    city: str
    state: str


@dataclass(frozen=True)
class SOSCandidate:
    shoot_id: int
    name: str
    start_date: str
    end_date: str
    locations: tuple[SOSLocation, ...]

    @property
    def is_minnesota(self) -> bool:
        return any(location.state == "MN" for location in self.locations)


@dataclass
class SOSImportResult:
    shoot_id: int
    shoot_name: str
    events_found: int = 0
    score_rows_found: int = 0
    score_rows_imported: int = 0
    shooters_created: int = 0
    observations_written: int = 0
    warnings: list[str] = field(default_factory=list)


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, separators=(",", ":")).encode("utf-8")


def _error_message(exc: HTTPError) -> str:
    try:
        payload = json.loads(exc.read().decode("utf-8", errors="replace"))
        message = payload.get("error", {}).get("message") or payload.get("payload")
        if message:
            return str(message)
    except Exception:
        pass
    return f"HTTP {exc.code} {exc.reason}"


class SOSClient:
    """Authenticated read client for the SOS Clays shooter-facing API.

    Credentials are used only for the Firebase sign-in request and are never
    retained on this object. ID/refresh tokens live in memory for this process.
    """

    def __init__(self, *, api_key: str = FIREBASE_API_KEY, timeout: int = 30):
        self.api_key = api_key
        self.timeout = timeout
        self.id_token = ""
        self.refresh_token = ""
        self.local_id = ""
        self.expires_at = 0.0

    @property
    def authenticated(self) -> bool:
        return bool(self.id_token and self.local_id)

    def _request_json(
        self,
        method: str,
        url: str,
        *,
        payload: Any | None = None,
        headers: dict[str, str] | None = None,
        form: dict[str, str] | None = None,
    ) -> Any:
        request_headers = {
            "Accept": "application/json",
            "User-Agent": "MNTrapTeam/5.2",
        }
        request_headers.update(headers or {})
        data = None
        if form is not None:
            data = urlencode(form).encode("utf-8")
            request_headers["Content-Type"] = "application/x-www-form-urlencoded"
        elif payload is not None:
            data = _json_bytes(payload)
            request_headers["Content-Type"] = "application/json"

        request = Request(url, data=data, headers=request_headers, method=method)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise SOSAPIError(_error_message(exc)) from exc
        except Exception as exc:
            raise SOSAPIError(f"SOS request failed: {exc}") from exc

    def login(self, email: str, password: str) -> None:
        email = str(email or "").strip()
        if not email or not password:
            raise SOSAPIError("SOS email and password are required")
        response = self._request_json(
            "POST",
            f"{FIREBASE_LOGIN}?key={self.api_key}",
            payload={
                "email": email,
                "password": password,
                "returnSecureToken": True,
            },
        )
        self.id_token = str(response.get("idToken") or "")
        self.refresh_token = str(response.get("refreshToken") or "")
        self.local_id = str(response.get("localId") or "")
        self.expires_at = time.time() + int(response.get("expiresIn") or 3600)
        if not self.authenticated:
            raise SOSAPIError("SOS/Firebase login did not return a usable ID token")

    def _refresh(self) -> None:
        if not self.refresh_token:
            raise SOSAPIError("SOS session expired; sign in again")
        response = self._request_json(
            "POST",
            f"{FIREBASE_REFRESH}?key={self.api_key}",
            form={
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
            },
        )
        self.id_token = str(response.get("id_token") or "")
        self.refresh_token = str(response.get("refresh_token") or self.refresh_token)
        self.local_id = str(response.get("user_id") or self.local_id)
        self.expires_at = time.time() + int(response.get("expires_in") or 3600)
        if not self.id_token:
            raise SOSAPIError("SOS token refresh failed")

    def _auth_headers(self) -> dict[str, str]:
        if not self.authenticated:
            raise SOSAPIError("Sign in to SOS before requesting scores")
        if time.time() >= self.expires_at - 60:
            self._refresh()
        return {"Authorization": f"Bearer {self.id_token}"}

    @staticmethod
    def _payload(response: Any) -> Any:
        if not isinstance(response, dict):
            raise SOSAPIError("Unexpected SOS response")
        if response.get("success") is False:
            raise SOSAPIError(str(response.get("payload") or "SOS request failed"))
        return response.get("payload")

    def list_shoots_page(
        self,
        *,
        search: str = "",
        page_size: int = 100,
        page_index: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        query = urlencode(
            {
                "s": search,
                "ps": int(page_size),
                "pi": int(page_index),
                "uid": self.local_id,
            }
        )
        response = self._request_json(
            "POST",
            f"{API_BASE}/utilities/get-shoot-list/?{query}",
            payload={},
            headers=self._auth_headers(),
        )
        payload = self._payload(response)
        rows = payload if isinstance(payload, list) else []
        return rows, int(response.get("resultsLength") or len(rows))

    def iter_shoots(self, *, page_size: int = 100) -> Iterable[dict[str, Any]]:
        page = 0
        emitted = 0
        total = None
        while total is None or emitted < total:
            rows, total = self.list_shoots_page(
                page_size=page_size,
                page_index=page,
            )
            if not rows:
                break
            yield from rows
            emitted += len(rows)
            page += 1

    def get_shoot(self, shoot_id: int) -> dict[str, Any]:
        response = self._request_json(
            "GET",
            f"{API_BASE}/shoots/{int(shoot_id)}",
            headers=self._auth_headers(),
        )
        payload = self._payload(response)
        if not isinstance(payload, dict):
            raise SOSAPIError(f"Shoot {shoot_id}: invalid detail payload")
        return payload

    def high_gun_report(
        self,
        shoot_id: int,
        event_id: int,
        club_id: int,
    ) -> list[dict[str, Any]]:
        response = self._request_json(
            "POST",
            (
                f"{API_BASE}/shoots/{int(shoot_id)}/event/{int(event_id)}"
                f"/clubs/{int(club_id)}/highGunReport"
            ),
            payload={},
            headers=self._auth_headers(),
        )
        payload = self._payload(response)
        if not isinstance(payload, dict):
            return []
        rows = payload.get("sortedEventHighGunReportData")
        return rows if isinstance(rows, list) else []


def _locations(value: Any) -> tuple[SOSLocation, ...]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except Exception:
            value = []
    if isinstance(value, dict):
        value = list(value.values())
    if not isinstance(value, list):
        return ()
    result = []
    for item in value:
        if not isinstance(item, dict):
            continue
        raw_id = item.get("clubId") or item.get("id")
        try:
            club_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        result.append(
            SOSLocation(
                club_id=club_id,
                club_name=str(item.get("clubName") or item.get("name") or "").strip(),
                city=str(item.get("city") or "").strip(),
                state=str(item.get("stateProvince") or item.get("state") or "").upper(),
            )
        )
    return tuple(result)


def candidate_from_row(row: dict[str, Any]) -> SOSCandidate | None:
    try:
        shoot_id = int(row.get("shootId"))
    except (TypeError, ValueError):
        return None
    name = str(row.get("name") or "").strip()
    if not name:
        return None
    return SOSCandidate(
        shoot_id=shoot_id,
        name=name,
        start_date=str(row.get("startDate") or "")[:10],
        end_date=str(row.get("endDate") or "")[:10],
        locations=_locations(row.get("locations")),
    )


def target_year_window(season: int) -> tuple[date, date]:
    return date(season - 1, 9, 1), date(season, 8, 31)


def in_target_year(candidate: SOSCandidate, season: int) -> bool:
    try:
        start = datetime.strptime(candidate.start_date, "%Y-%m-%d").date()
        end = datetime.strptime(candidate.end_date, "%Y-%m-%d").date()
    except ValueError:
        return False
    low, high = target_year_window(season)
    return start >= low and end <= high


def discover_minnesota_shoots(client: SOSClient, season: int) -> list[SOSCandidate]:
    found = []
    for row in client.iter_shoots():
        candidate = candidate_from_row(row)
        if candidate and candidate.is_minnesota and in_target_year(candidate, season):
            found.append(candidate)
    return sorted(found, key=lambda item: (item.start_date, item.shoot_id))


def _event_items(shoot_payload: dict[str, Any]):
    events = shoot_payload.get("events") or {}
    if isinstance(events, list):
        for event in events:
            if isinstance(event, dict):
                yield str(event.get("eventId") or ""), event
        return
    if isinstance(events, dict):
        for key, event in events.items():
            if isinstance(event, dict):
                yield str(key), event


def _club_ids(event: dict[str, Any], fallback: tuple[SOSLocation, ...]) -> list[int]:
    club_events = event.get("clubEvents") or {}
    ids = []
    if isinstance(club_events, dict):
        for value in club_events:
            try:
                ids.append(int(value))
            except (TypeError, ValueError):
                pass
    if not ids:
        ids.extend(location.club_id for location in fallback)
    return list(dict.fromkeys(ids))


def _event_date(event: dict[str, Any], club_id: int, fallback: str) -> str:
    details = event.get("details") or {}
    club_events = event.get("clubEvents") or {}
    club_event = {}
    if isinstance(club_events, dict):
        club_event = club_events.get(str(club_id)) or club_events.get(club_id) or {}
    club_event_details = club_event.get("details") or {}
    for source in (club_event_details, club_event, details, event):
        if not isinstance(source, dict):
            continue
        for key in ("eventDate", "date", "startDate", "shootDate"):
            value = str(source.get(key) or "")[:10]
            if value:
                return value
    return fallback


def _display_name(row: dict[str, Any]) -> str:
    return " ".join(
        str(row.get(key) or "").strip()
        for key in ("firstName", "middleName", "lastName")
        if str(row.get(key) or "").strip()
    )


def _category(value: Any) -> str:
    code = str(value or "").strip().upper().replace("-", "_")
    aliases = {
        "": "MEN",
        "L": "LADY",
        "L1": "LADY_I",
        "L2": "LADY_II",
        "V": "VET",
        "VT": "VET",
        "SV": "SR_VET",
        "SRV": "SR_VET",
        "SJ": "SUB_JR",
        "J": "JUNIOR",
        "JR": "JUNIOR",
        "SBV": "SUB_VET",
    }
    return aliases.get(code, code or "MEN")


def _local_shoot(database, candidate: SOSCandidate) -> int:
    source_url = f"https://app.sosclays.com/shoots/shoot;shootId={candidate.shoot_id}"
    rows = database.query(
        "SELECT id FROM shoots WHERE source_url=? ORDER BY id LIMIT 1",
        (source_url,),
    )
    if rows:
        return int(rows[0]["id"])
    location = next((item for item in candidate.locations if item.state == "MN"), None)
    club = location.club_name if location else candidate.name
    city = location.city if location else ""
    state = location.state if location else ""
    existing = database.query(
        "SELECT id FROM shoots WHERE name=? AND start_date=? ORDER BY id LIMIT 1",
        (candidate.name, candidate.start_date),
    )
    if existing:
        database.execute(
            "UPDATE shoots SET source_url=COALESCE(NULLIF(source_url,''),?) WHERE id=?",
            (source_url, int(existing[0]["id"])),
        )
        return int(existing[0]["id"])
    return int(
        database.execute(
            """
            INSERT INTO shoots(name,club,city,state,start_date,end_date,source_type,source_url)
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                candidate.name,
                club,
                city,
                state,
                candidate.start_date,
                candidate.end_date,
                "SOS Clays",
                source_url,
            ),
        )
    )


def import_sos_shoot(
    database,
    client: SOSClient,
    candidate: SOSCandidate,
    season: int,
    *,
    mn_only: bool = True,
) -> SOSImportResult:
    details = client.get_shoot(candidate.shoot_id)
    local_shoot_id = _local_shoot(database, candidate)
    result = SOSImportResult(candidate.shoot_id, candidate.name)
    aggregates: dict[tuple[int, str], dict[str, Any]] = {}
    mn_location = next((item for item in candidate.locations if item.state == "MN"), None)
    club_name = mn_location.club_name if mn_location else candidate.name

    for key, event in _event_items(details):
        event_details = event.get("details") or {}
        try:
            event_id = int(event.get("eventId") or key)
            event_type = int(event_details.get("eventTypeId"))
            targets = int(event_details.get("targetQuantity") or 0)
        except (TypeError, ValueError):
            result.warnings.append(f"Skipped malformed SOS event {key}")
            continue
        discipline = EVENT_TYPES.get(event_type)
        if not discipline or targets <= 0:
            continue
        result.events_found += 1
        event_number = event_details.get("eventNumber")
        event_label = str(event_details.get("name") or f"Event {event_id}").strip()
        stored_name = (
            f"E{event_number} - {event_label}" if event_number not in (None, "") else event_label
        )

        for club_id in _club_ids(event, candidate.locations):
            rows = client.high_gun_report(candidate.shoot_id, event_id, club_id)
            result.score_rows_found += len(rows)
            event_date = _event_date(event, club_id, candidate.start_date)

            for row in rows:
                if not isinstance(row, dict):
                    continue
                state = str(row.get("stateProvince") or "").upper()
                if mn_only and state != "MN":
                    continue
                ata = normalize_ata(row.get("ataId"))
                name = _display_name(row)
                if not ata:
                    result.warnings.append(f"Skipped SOS row without ATA number: {name or 'unknown'}")
                    continue
                score_value = row.get("totalScore")
                if score_value is None:
                    continue
                try:
                    hits = int(score_value)
                except (TypeError, ValueError):
                    continue
                if hits < 0 or hits > targets:
                    result.warnings.append(
                        f"Skipped invalid SOS score {name} E{event_number}: {hits}/{targets}"
                    )
                    continue

                shooter_rows = database.query(
                    "SELECT id FROM shooters WHERE ata_number=?",
                    (ata,),
                )
                if shooter_rows:
                    shooter_id = int(shooter_rows[0]["id"])
                else:
                    if not name:
                        result.warnings.append(f"Skipped ATA {ata}: SOS name is blank")
                        continue
                    yardage = row.get("handicap")
                    try:
                        yardage = float(yardage) if yardage not in (None, "") else None
                    except (TypeError, ValueError):
                        yardage = None
                    shooter_id = int(
                        database.upsert_shooter(
                            ata,
                            name,
                            _category(row.get("category")),
                            state or "MN",
                            yardage,
                        )
                    )
                    result.shooters_created += 1

                database.execute(
                    """
                    INSERT INTO scores(
                        shooter_id,shoot_id,event_date,event_name,discipline,
                        targets,hits,in_state,club_key,source,official,raw_name
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,0,?)
                    ON CONFLICT(shooter_id,shoot_id,event_name,discipline) DO UPDATE SET
                        event_date=excluded.event_date,
                        targets=excluded.targets,
                        hits=excluded.hits,
                        in_state=excluded.in_state,
                        club_key=excluded.club_key,
                        source=excluded.source,
                        official=0,
                        raw_name=excluded.raw_name
                    """,
                    (
                        shooter_id,
                        local_shoot_id,
                        event_date,
                        stored_name,
                        discipline,
                        targets,
                        hits,
                        int(state == "MN"),
                        club_name,
                        "SOS Clays",
                        name,
                    ),
                )
                result.score_rows_imported += 1

                aggregate = aggregates.setdefault(
                    (shooter_id, discipline),
                    {
                        "targets": 0,
                        "hits": 0,
                        "event_date": event_date,
                        "state": state,
                    },
                )
                aggregate["targets"] += targets
                aggregate["hits"] += hits
                aggregate["event_date"] = max(aggregate["event_date"], event_date)

    for (shooter_id, discipline), aggregate in aggregates.items():
        observe_event(
            database,
            shooter_id=shooter_id,
            season=season,
            event_date=aggregate["event_date"],
            shoot_name=candidate.name,
            shoot_number=str(candidate.shoot_id),
            discipline=discipline,
            targets=aggregate["targets"],
            hits=aggregate["hits"],
            source="SOS Clays",
            source_record_id=(
                f"sos:{candidate.shoot_id}:{shooter_id}:{discipline}"
            ),
            event_name="",
            club=club_name,
            state=aggregate["state"],
            in_state=aggregate["state"] == "MN",
            source_url=(
                f"https://app.sosclays.com/shoots/shoot;shootId={candidate.shoot_id}"
            ),
            official=False,
        )
        result.observations_written += 1

    return result


def candidate_for_shoot_id(
    client: SOSClient,
    shoot_id: int,
    *,
    page_size: int = 100,
) -> SOSCandidate:
    for row in client.iter_shoots(page_size=page_size):
        candidate = candidate_from_row(row)
        if candidate and candidate.shoot_id == int(shoot_id):
            return candidate
    raise SOSAPIError(f"SOS shoot {shoot_id} was not found in the shoot list")
