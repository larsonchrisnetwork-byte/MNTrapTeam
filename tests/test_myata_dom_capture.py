from mntrapteam.myata_dom_capture import _clean


def test_clean_text():
    assert _clean(" Aiden \n\n Weber ") == "Aiden\nWeber"
