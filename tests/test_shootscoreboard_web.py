from mntrapteam.shootscoreboard_web import (
    discover_event_ids,
    extract_shoot_id,
    load_public_shoot,
    parse_event_report,
    parse_shoot_header,
)


def read(name):
    return open(f"tests/fixtures/{name}", encoding="utf-8").read()


def test_extract_shoot_id():
    assert extract_shoot_id("1957") == 1957
    assert extract_shoot_id(
        "https://shootscoreboard.com/menu.cfm?shootid=1957"
    ) == 1957


def test_parse_realistic_shoot_header():
    name, start, end = parse_shoot_header(read("ssb_menu_1957.html"), 1957)
    assert name == "2025 MINNESOTA NORTHERN ZONE SHOOT"
    assert start == "2025-06-14"
    assert end == "2025-06-15"


def test_discover_event_ids():
    assert discover_event_ids(read("ssb_entries_1957.html"), 1957) == [1, 2, 3]


def test_parse_actual_report_shapes():
    singles = parse_event_report(read("ssb_event1_1957.html"), 1)
    handicap = parse_event_report(read("ssb_event2_1957.html"), 2)
    doubles = parse_event_report(read("ssb_event3_1957.html"), 3)
    assert singles.discipline == "singles"
    assert singles.entries[0]["targets"] == 200
    assert singles.entries[0]["hits"] == 198
    assert handicap.entries[0]["hits"] == 95
    assert doubles.entries[0]["targets"] == 100
    assert doubles.entries[0]["hits"] == 95


def test_load_shoot_with_injected_fetcher():
    files = {
        "menu.cfm": read("ssb_menu_1957.html"),
        "entrys.cfm": read("ssb_entries_1957.html"),
        "sorteventid=1": read("ssb_event1_1957.html"),
        "sorteventid=2": read("ssb_event2_1957.html"),
        "sorteventid=3": read("ssb_event3_1957.html"),
    }
    def fetcher(url):
        for key, value in files.items():
            if key in url:
                return value
        raise AssertionError(url)
    shoot = load_public_shoot(1957, fetcher=fetcher)
    assert shoot.name == "2025 MINNESOTA NORTHERN ZONE SHOOT"
    assert len(shoot.events) == 3
    assert sum(len(event.entries) for event in shoot.events) == 4
