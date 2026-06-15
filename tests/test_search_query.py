import csv
from pathlib import Path

from healthscan.search_query import search_prices


def workspace_tmp_path(name: str) -> Path:
    path = Path("data") / "tmp" / "tests" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write_search_fixture(path, rows) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "hospital",
                "procedure_name",
                "code_type",
                "code",
                "display_price",
                "display_price_type",
                "payer_name",
                "plan_name",
                "data_quality_flag",
                "source_url",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def test_search_prices_uses_translation_codes_for_socal_results() -> None:
    status, hits = search_prices("brain MRI", area="southern_california")

    assert status == "ok"
    assert len({hit.hospital for hit in hits}) >= 3
    assert all(hit.code_type in {"CPT", "HCPCS"} for hit in hits)


def test_search_prices_filters_by_care_setting() -> None:
    status, hits = search_prices("knee replacement", area="southern_california", care_setting="outpatient")

    assert status == "no_results"
    assert hits == []


def test_search_prices_rejects_unsupported_area() -> None:
    status, hits = search_prices("brain MRI", area="new_york")

    assert status == "not_supported_area"
    assert hits == []


def test_search_prices_filters_patient_irrelevant_rows_by_default() -> None:
    path = workspace_tmp_path("search-filtered.csv")
    write_search_fixture(
        path,
        [
            {
                "hospital": "Implausible Hospital",
                "procedure_name": "EKG",
                "code_type": "CPT",
                "code": "93000",
                "display_price": "1.00",
                "display_price_type": "negotiated",
                "payer_name": "",
                "plan_name": "",
                "data_quality_flag": "low_outlier",
                "source_url": "https://example.org/mrf.csv",
            },
            {
                "hospital": "Useful Hospital",
                "procedure_name": "EKG",
                "code_type": "CPT",
                "code": "93000",
                "display_price": "125.00",
                "display_price_type": "cash",
                "payer_name": "",
                "plan_name": "",
                "data_quality_flag": "ok",
                "source_url": "https://example.org/mrf.csv",
            },
        ],
    )

    status, hits = search_prices("EKG", area="southern_california", path=path)

    assert status == "ok"
    assert [hit.hospital for hit in hits] == ["Useful Hospital"]
    assert hits[0].user_relevance_flag == "display_ok"


def test_search_prices_can_include_filtered_rows_for_audits() -> None:
    path = workspace_tmp_path("search-include-filtered.csv")
    write_search_fixture(
        path,
        [
            {
                "hospital": "Implausible Hospital",
                "procedure_name": "EKG",
                "code_type": "CPT",
                "code": "93000",
                "display_price": "1.00",
                "display_price_type": "negotiated",
                "payer_name": "",
                "plan_name": "",
                "data_quality_flag": "low_outlier",
                "source_url": "https://example.org/mrf.csv",
            },
        ],
    )

    status, hits = search_prices("EKG", area="southern_california", path=path, include_filtered=True)

    assert status == "ok"
    assert hits[0].user_relevance_flag == "excluded_low_outlier"
