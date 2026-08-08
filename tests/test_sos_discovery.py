from mntrapteam.sos_discovery import _summary


def test_summary_dict_lists_keys_without_values():
    value = {
        "ShootId": 123,
        "Shooters": [
            {"AtaNumber": "1234567", "Name": "Example", "Score": 99}
        ],
    }
    result = _summary(value)
    assert result["ShootId"]["type"] == "int"
    assert result["Shooters"]["count"] == 1
    assert "AtaNumber" in result["Shooters"]["first_item_keys"]


def test_summary_list_shape():
    value = [{"id": 1, "name": "shoot"}]
    result = _summary(value)
    assert result["count"] == 1
    assert "id" in result["first_item_keys"]
