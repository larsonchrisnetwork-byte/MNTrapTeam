from mntrapteam.projected_ranking import apply_projected_ranking

def test_highest_average_first_even_if_ineligible():
    rows = [
        {"display_name": "Eligible", "live_hoa": 92.0, "eligible": True},
        {"display_name": "Partial", "live_hoa": 95.0, "eligible": False},
        {"display_name": "Eligible Two", "live_hoa": 93.0, "eligible": True},
    ]
    result = apply_projected_ranking(rows, 2)
    assert [r["display_name"] for r in result["rows"]] == [
        "Partial", "Eligible Two", "Eligible"
    ]
    assert result["rows"][0]["projected_rank"] == 1
    assert result["rows"][0]["eligible_rank"] is None

def test_projected_and_eligible_cuts_are_separate():
    rows = [
        {"display_name": "A", "live_hoa": 96.0, "eligible": False},
        {"display_name": "B", "live_hoa": 95.0, "eligible": True},
        {"display_name": "C", "live_hoa": 94.0, "eligible": True},
    ]
    result = apply_projected_ranking(rows, 2)
    assert result["projected_cut_hoa"] == 95.0
    assert result["eligible_cut_hoa"] == 94.0
