from healthscan.local_sources import resolve_local_source


def test_resolve_local_source_returns_none_for_unknown_url() -> None:
    assert resolve_local_source("https://example.org/nope.csv") is None


def test_resolve_local_source_finds_rady_csv() -> None:
    source = resolve_local_source(
        "https://www.rchsd.org/wp-content/uploads/2026/03/"
        "95-1691313_rady-childrens-hospital-san-diego_standardcharges.csv"
    )

    assert source is not None
    assert source.mrf_format == "csv"


def test_resolve_local_source_finds_keck_wrapped_download_full_csv() -> None:
    source = resolve_local_source(
        "https://hospitalpricedisclosure.com/download.aspx?pi=5fSixiuBb0ZpZwZgOthF7A*-*"
    )

    assert source is not None
    assert source.scan_scope == "full_local_csv"


def test_resolve_local_source_finds_cedars_large_json() -> None:
    source = resolve_local_source(
        "https://www.cedars-sinai.org/content/dam/cedars-sinai/billing-insurance/documents/"
        "951644600_CEDARS-SINAI-MEDICAL-CENTER_standardcharges.json"
    )

    assert source is not None
    assert source.mrf_format == "json"
    assert source.scan_scope == "large_local_json"
