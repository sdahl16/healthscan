from healthscan.relevance import assess_price_relevance


def test_assess_price_relevance_keeps_ok_rows() -> None:
    result = assess_price_relevance({"data_quality_flag": "ok"})

    assert result.is_user_relevant is True
    assert result.user_relevance_flag == "display_ok"


def test_assess_price_relevance_excludes_low_outliers() -> None:
    result = assess_price_relevance({"data_quality_flag": "low_outlier"})

    assert result.is_user_relevant is False
    assert result.user_relevance_flag == "excluded_low_outlier"
