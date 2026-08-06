
from pathlib import Path


def gui_source() -> str:
    return Path("mntrapteam/gui.py").read_text(encoding="utf-8")


def test_gui_wires_progress_and_race_engines():
    source = gui_source()
    assert "from .analytics import personal_progress" in source
    assert "from .race import team_race" in source
    assert "self.progress=self.make_progress()" in source
    assert "self.race=self.make_race()" in source


def test_gui_has_progress_and_race_tabs():
    source = gui_source()
    assert "def make_progress(self):" in source
    assert "def refresh_progress(self):" in source
    assert "def make_race(self):" in source
    assert "def refresh_race(self):" in source


def test_gui_refreshes_both_dashboards():
    source = gui_source()
    refresh_line = next(
        line for line in source.splitlines()
        if line.strip().startswith("def refresh_all(self):")
    )
    assert "self.refresh_progress()" in refresh_line
    assert "self.refresh_race()" in refresh_line


def test_version_matches_current_release():
    assert Path("VERSION").read_text(encoding="utf-8").strip() == "2.1.0"
    assert "MNTrapTeam 2.1.0" in gui_source()
