from mntrapteam.myata_search_capture import _shape


def test_shape_member_summary():
    body = [
        {
            "Year": 2026,
            "SinglesShot": 1500,
            "HandicapShot": 1200,
            "DoublesShot": 1000,
        }
    ]
    result = _shape(body)
    assert result["type"] == "list"
    assert result["count"] == 1
    assert "SinglesShot" in result["first_item_keys"]
