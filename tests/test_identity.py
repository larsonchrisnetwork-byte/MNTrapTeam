from mntrapteam.identity import (
    normalize_ata,
    same_shooter,
    safe_identity_match,
)

def test_leading_zeroes_are_preserved():
    assert normalize_ata("0113918") == "0113918"

def test_names_do_not_override_ata():
    assert not safe_identity_match(
        "1625056",
        "9999999",
        expected_name="Joel Johnson",
        candidate_name="Joel Johnson",
    )

def test_exact_ata_is_identity():
    assert same_shooter("1625056", "1625056")
