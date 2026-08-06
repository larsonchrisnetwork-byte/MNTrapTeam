from mntrapteam.ata_haa_pdf import category_from_text, _valid_ata


def test_category_mapping():
    assert category_from_text("HAA SUB JUNIOR") == "SUB_JR"
    assert category_from_text("HAA LADY I") == "LADY_I"
    assert category_from_text("HAA LADY II") == "LADY_II"
    assert category_from_text("HAA SENIOR VETERAN") == "SENIOR_VETERAN"
    assert category_from_text("HAA - CLASS AAA") == "MEN"


def test_ata_number_cleanup():
    assert _valid_ata("1,316,740") == "1316740"
    assert _valid_ata("215301") == "215301"
    assert _valid_ata("#N/A") == ""
    assert _valid_ata("12") == ""
