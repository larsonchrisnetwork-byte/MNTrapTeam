from mntrapteam.myata_broad_capture import _shape


def test_shape_summary_list():
    value = [
        {
            "Year": 2026,
            "SinglesShot": 1600,
            "SinglesHitPercentage": 96.0,
        }
    ]
    result = _shape(value)
    assert result["type"] == "list"
    assert result["count"] == 1
    assert "Year" in result["first_item_keys"]
    assert "SinglesShot" in result["first_item_keys"]
