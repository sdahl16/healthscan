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


def test_resolve_local_source_finds_next_ten_sources() -> None:
    cases = [
        (
            "https://www.hollywoodpresbyterian.com/"
            "300284087_HOLLYWOOD-PRESBYTERIAN-MEDICAL-CENTER_STANDARDCHARGES.json",
            "json",
            "large_local_json",
        ),
        (
            "https://media.huntingtonhealth.org/951644036_HUNTINGTON-HOSPITAL_standardcharges.csv",
            "csv",
            "full_local_csv",
        ),
        (
            "https://www.ucihealth.org/pricetransparency/"
            "952226406_regents-of-the-university-of-california-at-irvine-hospital_standardcharges.json",
            "json",
            "large_local_json",
        ),
        (
            "https://downloads.ctfassets.net/8u2cuf59smsh/52tazi7symInZOZZ2g2eJU/"
            "a5edeceac81a9d8369ea9548032e2d42/"
            "951643327_hoag-memorial-hospital-presbyterian_standardcharges.csv",
            "csv",
            "full_local_csv",
        ),
        (
            "https://www.memorialcare.org/sites/default/files/_images/content/Patient-Financial-Services/"
            "330687414_memorialcare-orange-coast-medical-center_standardcharges.json",
            "json",
            "large_local_json",
        ),
        (
            "https://pricetransparency.healthcare/llu-mc/charges/export",
            "csv",
            "full_local_csv",
        ),
        (
            "https://stctrprodsnsvc00455826e6.blob.core.windows.net/pt-final-posting-files/"
            "33-0751869_RIVERSIDE-COMMUNITY-HOSPITAL_standardcharges.json?token=redacted",
            "json",
            "large_local_json",
        ),
        (
            "https://tricitymed.org/wp-content/uploads/2026/03/"
            "952126937_Tri-City-Medical-Center_standardcharges.csv",
            "csv",
            "full_local_csv",
        ),
        (
            "https://stctrprodsnsvc00455826e6.blob.core.windows.net/pt-final-posting-files/"
            "95-2321136_LOS-ROBLES-HOSPITAL-AND-MEDICAL-CENTER_standardcharges.json?token=redacted",
            "json",
            "large_local_json",
        ),
        (
            "https://www.mycmh.org/documents/"
            "951683892_community-memorial-healthcare-ventura_standardcharges.csv.csv",
            "csv",
            "full_local_csv",
        ),
    ]

    for url, expected_format, expected_scope in cases:
        source = resolve_local_source(url)
        assert source is not None, url
        assert source.mrf_format == expected_format
        assert source.scan_scope == expected_scope


def test_resolve_local_source_finds_phase1_san_diego_sources() -> None:
    cases = [
        (
            "https://apps.scripps.org/pricetransparency/"
            "951684089_Scripps-Memorial-Hospital-La-Jolla_standardcharges.csv",
            "csv",
            "full_local_csv",
        ),
        (
            "https://apps.scripps.org/pricetransparency/"
            "951684089_Scripps-Mercy-Hospital-San-Diego_standardcharges.csv",
            "csv",
            "full_local_csv",
        ),
        (
            "https://downloads.ctfassets.net/pxcfulgsd9e2/7kOO19WgXRFqOFfWyPsSCE/"
            "1dd67ee60fbf2a34d729812c39abb1fe/95-3782169_sharp-memorial-hospital_standardcharges.csv",
            "csv",
            "full_local_csv",
        ),
        (
            "https://downloads.ctfassets.net/pxcfulgsd9e2/pDe4LFVvP8fh5nOJd8Zji/"
            "71b0885eb86902c17aee42e048ea796b/33-0449527_grossmont-hospital-corporation_standardcharges.csv",
            "csv",
            "full_local_csv",
        ),
        (
            "https://paradisevalleyhospital.com/wp-content/uploads/2026/04/"
            "205837239_ParadiseValleyHospital_standardcharges.JSON",
            "json",
            "large_local_json",
        ),
    ]

    for url, expected_format, expected_scope in cases:
        source = resolve_local_source(url)
        assert source is not None, url
        assert source.mrf_format == expected_format
        assert source.scan_scope == expected_scope
