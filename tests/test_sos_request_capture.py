from mntrapteam.sos_request_capture import _sanitize_post_data


def test_sanitize_json_keeps_event_filters():
    result = _sanitize_post_data(
        '{"eventIds":[17360,17361,19241],"reportType":"HAA"}'
    )
    assert result["eventIds"] == [17360, 17361, 19241]
    assert result["reportType"] == "HAA"


def test_sanitize_redacts_sensitive_keys():
    result = _sanitize_post_data(
        '{"authorization":"secret","eventIds":[1,2,3]}'
    )
    assert result["authorization"] == "<redacted>"
    assert result["eventIds"] == [1, 2, 3]
