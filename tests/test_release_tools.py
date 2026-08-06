from pathlib import Path

import pytest

from mntrapteam.release_tools import (
    gui_version,
    obsolete_upgrade_files,
    package_version,
    project_version,
)


def project(tmp_path, version="2.3.0", gui_version_value="2.3.0"):
    (tmp_path / "mntrapteam").mkdir()
    (tmp_path / "VERSION").write_text(version + "\n", encoding="utf-8")
    (tmp_path / "mntrapteam" / "gui.py").write_text(
        f"TITLE='MNTrapTeam {gui_version_value}'\n",
        encoding="utf-8",
    )
    (tmp_path / "mntrapteam" / "__init__.py").write_text(
        f'__version__="{version}"\n',
        encoding="utf-8",
    )


def test_project_version_validation(tmp_path):
    project(tmp_path)
    assert project_version(tmp_path) == "2.3.0"
    (tmp_path / "VERSION").write_text("version two", encoding="utf-8")
    with pytest.raises(ValueError):
        project_version(tmp_path)


def test_gui_and_package_versions(tmp_path):
    project(tmp_path)
    assert gui_version(tmp_path) == "2.3.0"
    assert package_version(tmp_path) == "2.3.0"


def test_obsolete_upgrade_files_keep_current_patch(tmp_path):
    project(tmp_path)
    (tmp_path / "Apply_v2.2.0.py").write_text("", encoding="utf-8")
    (tmp_path / "Apply_v2.3.0.py").write_text("", encoding="utf-8")
    (tmp_path / "README_V2_2_UPGRADE.md").write_text("", encoding="utf-8")

    found = {path.name for path in obsolete_upgrade_files(tmp_path)}
    assert "Apply_v2.2.0.py" in found
    assert "README_V2_2_UPGRADE.md" in found
    assert "Apply_v2.3.0.py" not in found
