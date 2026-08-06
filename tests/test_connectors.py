from pathlib import Path

from mntrapteam.connectors import (
    PROVIDERS,
    SessionStore,
    infer_authentication,
    provider_for,
)


def test_provider_lookup():
    assert provider_for("sos").display_name == "SOS Clays"
    assert provider_for("shootata").display_name == "MyATA"
    assert provider_for("ata_scores").display_name == "ATA Scores"


def test_session_store_is_provider_specific(tmp_path):
    store = SessionStore(tmp_path)
    sos = store.profile_dir("sos")
    ata = store.profile_dir("shootata")
    assert sos != ata
    assert sos.parent.name == "browser_sessions"


def test_metadata_round_trip(tmp_path):
    store = SessionStore(tmp_path)
    store.write_metadata(
        "sos",
        {
            "last_url": "https://app.sosclays.com/dashboard",
            "last_checked": "2026-08-06T15:00:00",
            "likely_authenticated": True,
            "detail": "Dashboard visible",
        },
    )
    status = store.status("sos")
    assert status.likely_authenticated is True
    assert "dashboard" in status.last_url


def test_clear_only_selected_provider(tmp_path):
    store = SessionStore(tmp_path)
    (store.profile_dir("sos") / "cookie").write_text("x")
    (store.profile_dir("shootata") / "cookie").write_text("y")
    assert store.clear("sos") is True
    assert not (store.root / "sos").exists()
    assert (store.root / "shootata").exists()


def test_auth_inference_login_pages():
    sos = PROVIDERS["sos"]
    value, detail = infer_authentication(
        sos,
        "https://app.sosclays.com/login",
        "Sign In Email Password",
    )
    assert value is False

    ata = PROVIDERS["shootata"]
    value, detail = infer_authentication(
        ata,
        "https://shootata.com/Shooter-Information-Center",
        "Please login to see your scores ATA Number Password",
    )
    assert value is False


def test_auth_inference_authenticated_content():
    ata = PROVIDERS["shootata"]
    value, detail = infer_authentication(
        ata,
        "https://shootata.com/Shooter-Information-Center",
        "My Scores Detailed Information Target Year",
    )
    assert value is True

    scores = PROVIDERS["ata_scores"]
    value, detail = infer_authentication(
        scores,
        "https://scores.shootata.com/",
        "2026 Grand American",
    )
    assert value is True
