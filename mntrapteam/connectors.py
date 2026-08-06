from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import json
import shutil
import time


@dataclass(frozen=True)
class Provider:
    key: str
    display_name: str
    login_url: str
    home_url: str
    authenticated_url_hints: tuple[str, ...]
    login_url_hints: tuple[str, ...]
    login_text_hints: tuple[str, ...]


PROVIDERS: dict[str, Provider] = {
    "sos": Provider(
        key="sos",
        display_name="SOS Clays",
        login_url="https://app.sosclays.com/login",
        home_url="https://app.sosclays.com/",
        authenticated_url_hints=("/dashboard", "/shoot", "/event", "/profile"),
        login_url_hints=("/login",),
        login_text_hints=("sign in", "email", "password"),
    ),
    "shootata": Provider(
        key="shootata",
        display_name="MyATA",
        login_url="https://shootata.com/My-ATA",
        home_url="https://shootata.com/Shooter-Information-Center",
        authenticated_url_hints=(
            "/Shooter-Information-Center",
            "/My-ATA",
        ),
        login_url_hints=("/My-ATA",),
        login_text_hints=("ata number", "password", "forgot password"),
    ),
    "ata_scores": Provider(
        key="ata_scores",
        display_name="ATA Scores",
        login_url="https://scores.shootata.com/",
        home_url="https://scores.shootata.com/",
        authenticated_url_hints=("/",),
        login_url_hints=(),
        login_text_hints=(),
    ),
}


@dataclass
class SessionStatus:
    provider: str
    display_name: str
    profile_path: str
    profile_exists: bool
    last_url: str
    last_checked: str
    likely_authenticated: bool | None
    detail: str


class ConnectorError(RuntimeError):
    pass


def provider_for(key: str) -> Provider:
    normalized = str(key or "").strip().lower()
    if normalized not in PROVIDERS:
        raise ValueError(
            f"Unknown provider {key!r}. Choose from: {', '.join(PROVIDERS)}"
        )
    return PROVIDERS[normalized]


class SessionStore:
    def __init__(self, data_dir: Path):
        self.root = Path(data_dir) / "browser_sessions"
        self.root.mkdir(parents=True, exist_ok=True)

    def profile_dir(self, provider_key: str) -> Path:
        provider_for(provider_key)
        path = self.root / provider_key
        path.mkdir(parents=True, exist_ok=True)
        return path

    def metadata_path(self, provider_key: str) -> Path:
        return self.profile_dir(provider_key) / "mntrapteam_session.json"

    def read_metadata(self, provider_key: str) -> dict[str, Any]:
        path = self.metadata_path(provider_key)
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def write_metadata(self, provider_key: str, payload: dict[str, Any]) -> None:
        path = self.metadata_path(provider_key)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def clear(self, provider_key: str) -> bool:
        path = self.root / provider_key
        if not path.exists():
            return False
        shutil.rmtree(path)
        return True

    def status(self, provider_key: str) -> SessionStatus:
        provider = provider_for(provider_key)
        path = self.root / provider_key
        metadata = self.read_metadata(provider_key) if path.exists() else {}
        return SessionStatus(
            provider=provider.key,
            display_name=provider.display_name,
            profile_path=str(path),
            profile_exists=path.exists() and any(path.iterdir()),
            last_url=str(metadata.get("last_url") or ""),
            last_checked=str(metadata.get("last_checked") or ""),
            likely_authenticated=metadata.get("likely_authenticated"),
            detail=str(metadata.get("detail") or "Not checked"),
        )


def _load_playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise ConnectorError(
            "Playwright is not installed. Run Install_MNTrapTeam.bat again, "
            "then install the browser with: "
            '& ".\\.venv\\Scripts\\python.exe" -m playwright install chromium'
        ) from exc
    return sync_playwright


def infer_authentication(
    provider: Provider,
    url: str,
    page_text: str,
) -> tuple[bool | None, str]:
    url_lower = str(url or "").lower()
    text_lower = " ".join(str(page_text or "").lower().split())

    if provider.key == "ata_scores":
        return True, "ATA Scores is currently publicly accessible"

    if any(hint.lower() in url_lower for hint in provider.login_url_hints):
        if all(hint in text_lower for hint in provider.login_text_hints[:2]):
            return False, "Login form is visible"

    login_hits = sum(hint in text_lower for hint in provider.login_text_hints)
    if login_hits >= 2:
        return False, "Login fields or login instructions are visible"

    if provider.key == "sos":
        if "/login" not in url_lower and "sign in" not in text_lower:
            return True, "SOS login page is no longer visible"
    elif provider.key == "shootata":
        if "please login to see your scores" in text_lower:
            return False, "ShootATA reports that login is required"

        authenticated_markers = (
            "my scores",
            "search/buddies",
            "quick list",
            "all american",
            "detailed information",
        )

        if any(marker in text_lower for marker in authenticated_markers):
            return True, "Authenticated Shooter Information Center controls are visible"

    return None, "Authentication state could not be determined automatically"


def connect_interactively(
    data_dir: Path,
    provider_key: str,
    *,
    start_url: str | None = None,
    timeout_seconds: int = 600,
) -> SessionStatus:
    provider = provider_for(provider_key)
    store = SessionStore(data_dir)
    profile = store.profile_dir(provider.key)
    sync_playwright = _load_playwright()

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile),
            headless=False,
            viewport={"width": 1400, "height": 900},
            args=["--start-maximized"],
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(start_url or provider.login_url, wait_until="domcontentloaded")
        print(
            f"{provider.display_name} opened in a secure local browser profile.\n"
            "Log in directly on the provider's website. "
            "Return to this console and press Enter when finished."
        )
        input()
        try:
            page.wait_for_load_state("domcontentloaded", timeout=15000)
        except Exception:
            pass

        body_text = ""
        try:
            body_text = page.locator("body").inner_text(timeout=10000)

            control_labels = []
            controls = page.locator(
                "button, input[type=button], input[type=submit], "
                "a, [role=button]"
            )
            for index in range(min(controls.count(), 200)):
                control = controls.nth(index)
                label = (
                    control.get_attribute("value")
                    or control.get_attribute("aria-label")
                    or control.get_attribute("title")
                    or control.inner_text(timeout=1000)
                    or ""
                )
                label = " ".join(label.split())
                if label:
                    control_labels.append(label)

            body_text += "\n" + "\n".join(control_labels)
        except Exception:
            pass
        likely, detail = infer_authentication(provider, page.url, body_text)
        payload = {
            "provider": provider.key,
            "last_url": page.url,
            "last_checked": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "likely_authenticated": likely,
            "detail": detail,
        }
        store.write_metadata(provider.key, payload)
        context.close()

    return store.status(provider.key)


def check_session(
    data_dir: Path,
    provider_key: str,
    *,
    timeout_seconds: int = 45,
) -> SessionStatus:
    provider = provider_for(provider_key)
    store = SessionStore(data_dir)
    profile = store.profile_dir(provider.key)
    sync_playwright = _load_playwright()

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile),
            headless=True,
            viewport={"width": 1280, "height": 800},
        )
        page = context.pages[0] if context.pages else context.new_page()
        try:
            page.goto(
                provider.home_url,
                wait_until="domcontentloaded",
                timeout=timeout_seconds * 1000,
            )
            body_text = page.locator("body").inner_text(timeout=10000)

            labels = []
            controls = page.locator(
                "button, input[type=button], input[type=submit], "
                "a, [role=button]"
            )
            for index in range(min(controls.count(), 200)):
                control = controls.nth(index)
                label = (
                    control.get_attribute("value")
                    or control.get_attribute("aria-label")
                    or control.get_attribute("title")
                    or control.inner_text(timeout=1000)
                    or ""
                )
                label = " ".join(label.split())
                if label:
                    labels.append(label)

            body_text += "\n" + "\n".join(labels)
            likely, detail = infer_authentication(
                provider,
                page.url,
                body_text,
            )
        except Exception as exc:
            likely = None
            detail = f"Session check failed: {exc}"
        payload = {
            "provider": provider.key,
            "last_url": page.url,
            "last_checked": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "likely_authenticated": likely,
            "detail": detail,
        }
        store.write_metadata(provider.key, payload)
        context.close()

    return store.status(provider.key)


def status_rows(data_dir: Path) -> list[dict[str, Any]]:
    store = SessionStore(data_dir)
    return [asdict(store.status(key)) for key in PROVIDERS]
