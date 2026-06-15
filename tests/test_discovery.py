from healthscan.discovery import (
    cms_hpt_candidates,
    cms_hpt_url,
    extract_links,
    likely_mrf_links,
    source_page_candidates,
)


def test_cms_hpt_url_from_domain() -> None:
    assert cms_hpt_url("example.org") == "https://example.org/cms-hpt.txt"


def test_cms_hpt_candidates_include_www_fallback() -> None:
    assert cms_hpt_candidates("example.org") == (
        "https://example.org/cms-hpt.txt",
        "https://www.example.org/cms-hpt.txt",
    )


def test_source_page_candidates_include_price_transparency_paths() -> None:
    candidates = source_page_candidates("example.org")

    assert "https://example.org/price-transparency" in candidates
    assert "https://www.example.org/standard-charges" in candidates


def test_cms_hpt_url_preserves_direct_file_url() -> None:
    assert cms_hpt_url("https://example.org/cms-hpt.txt") == "https://example.org/cms-hpt.txt"


def test_extract_links_from_plain_text_and_html() -> None:
    body = """
    https://example.org/charges.csv
    <a href="/other.json">download</a>
    """

    assert extract_links(body, "https://example.org/cms-hpt.txt") == (
        "https://example.org/charges.csv",
        "https://example.org/other.json",
    )


def test_extract_links_from_cms_hpt_key_value_text() -> None:
    body = (
        "location-name: Example Hospital "
        "mrf-url: https://cdn.example.org/123_standardcharges.csv "
        "contact-email: example@example.org"
    )

    assert extract_links(body, "https://example.org/cms-hpt.txt") == (
        "https://cdn.example.org/123_standardcharges.csv",
    )


def test_likely_mrf_links_filters_supported_file_types() -> None:
    links = (
        "https://example.org/readme.txt",
        "https://example.org/charges.csv",
        "https://example.org/charges.json",
        "https://example.org/archive.zip",
        "https://example.org/download.aspx?file=standardcharges",
        "https://example.org/MRFDownload/system/system",
    )

    assert likely_mrf_links(links) == (
        "https://example.org/charges.csv",
        "https://example.org/charges.json",
        "https://example.org/archive.zip",
        "https://example.org/download.aspx?file=standardcharges",
        "https://example.org/MRFDownload/system/system",
    )
