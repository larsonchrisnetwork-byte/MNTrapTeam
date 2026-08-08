from mntrapteam.scoreboard_listing import (
    classify_zone,
    parse_listing,
)


def test_classifies_zone_hosts():
    assert classify_zone(
        "2026 Minnesota Southern Zone Shoot Lester Prairie 06/20/2026"
    ) == "SOUTHERN"
    assert classify_zone(
        "2026 Central Zone Beaverbrook 06/20/2026"
    ) == "CENTRAL"
    assert classify_zone(
        "2026 Northern Zone Grand Rapids 06/20/2026"
    ) == "NORTHERN"


def test_parses_shoot_ids_from_listing_rows():
    html = """
    <table>
      <tr>
        <td>2026 Minnesota Southern Zone Shoot</td>
        <td>Lester Prairie, MN</td>
        <td>06/20/2026 - 06/21/2026</td>
        <td><a href="reports.cfm?shootid=2044">SCORES</a></td>
      </tr>
    </table>
    """
    rows = parse_listing(html)
    assert len(rows) == 1
    assert rows[0].shoot_id == 2044
    assert "Southern Zone" in rows[0].text
