import pytest

from mntrapteam.database import Database


@pytest.fixture
def database(tmp_path):
    """Provide each test with a new isolated SQLite database."""
    return Database(tmp_path / "mntrapteam_test.db")