from mntrapteam.zone_haa_live import _category, _zone_from_name


def test_zone_detection():
    assert _zone_from_name("2026 Minnesota Southern Zone Shoot") == "SOUTHERN"
    assert _zone_from_name("Beaverbrook Central Zone") == "CENTRAL"
    assert _zone_from_name("Grand Rapids Northern Zone") == "NORTHERN"


def test_category_normalization():
    assert _category("") == "MEN"
    assert _category("SJ") == "SUB_JR"
    assert _category("SUBV") == "SUB_VET"
    assert _category("SRVT") == "SR_VET"
