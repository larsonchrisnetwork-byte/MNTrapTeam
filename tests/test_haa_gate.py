from mntrapteam.haa_gate import HAARecord, normalize_route, normalize_zone


def record(**overrides):
    values = dict(
        season=2026,
        shooter_id=1,
        route="ZONE",
        shoot_name="Southern Zone",
        shoot_date="2026-06-20",
        shoot_zone="SOUTHERN",
        resident_zone="SOUTHERN",
        category="MEN",
        singles_completed=True,
        handicap_completed=True,
        doubles_completed=True,
    )
    values.update(overrides)
    return HAARecord(**values)


def test_resident_zone_haa_qualifies():
    assert record().qualifies is True


def test_wrong_zone_does_not_qualify():
    value = record(resident_zone="CENTRAL")
    assert value.components_complete is True
    assert value.route_matches is False
    assert value.qualifies is False


def test_state_shoot_qualifies_regardless_of_resident_zone():
    value = record(
        route="STATE",
        shoot_name="Minnesota State Shoot",
        shoot_zone="",
        resident_zone="NORTHERN",
    )
    assert value.qualifies is True


def test_incomplete_components_do_not_qualify():
    assert record(doubles_completed=False).qualifies is False


def test_sub_junior_does_not_require_doubles():
    value = record(category="SUB_JR", doubles_completed=False)
    assert value.components_complete is True
    assert value.qualifies is True


def test_unverified_record_does_not_qualify():
    assert record(verified=False).qualifies is False


def test_normalization():
    assert normalize_zone("S") == "SOUTHERN"
    assert normalize_zone("central zone") == "CENTRAL"
    assert normalize_route("state shoot") == "STATE"
    assert normalize_route("resident zone") == "ZONE"
