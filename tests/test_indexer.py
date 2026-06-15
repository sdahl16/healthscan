from healthscan.indexer import (
    parse_amount,
    prices_from_record,
    prices_from_standard_charge_item,
    quality_flag_for_amount,
    record_matches,
)


def test_record_matches_flat_code_fields() -> None:
    record = {"code_type": "DRG", "code": "470"}

    assert record_matches(record, code_type="DRG", code="470")


def test_record_matches_nested_code_fields() -> None:
    record = {"codes": [{"type": "CPT", "code": "27130"}, {"type": "DRG", "code": "470"}]}

    assert record_matches(record, code_type="DRG", code="470")


def test_record_matches_ms_drg_for_drg_search() -> None:
    record = {"code_information": [{"type": "MS-DRG", "code": "470"}]}

    assert record_matches(record, code_type="DRG", code="470")


def test_record_matches_2026_csv_code_columns() -> None:
    record = {"code|1": "470", "code|1|type": "MS-DRG"}

    assert record_matches(record, code_type="DRG", code="470")


def test_record_matches_hcpcs_for_cpt_search() -> None:
    record = {"code|1": "70551", "code|1|type": "HCPCS"}

    assert record_matches(record, code_type="CPT", code="70551")


def test_parse_amount_rejects_placeholder_values() -> None:
    assert parse_amount("$12,345.67") == 12345.67
    assert parse_amount("999999999") is None


def test_quality_flag_marks_drg_low_outliers() -> None:
    assert quality_flag_for_amount(amount=1.93, code_type="DRG", price_type="negotiated_min") == "low_outlier"
    assert quality_flag_for_amount(amount=2175, code_type="DRG", price_type="negotiated_min") == "ok"


def test_quality_flag_marks_high_outliers() -> None:
    assert quality_flag_for_amount(amount=750000, code_type="CPT", price_type="gross") == "high_outlier"


def test_prices_from_record_normalizes_price_rows() -> None:
    record = {
        "description": "Major joint replacement",
        "code_type": "DRG",
        "code": "470",
        "gross_charge": "$100,000",
        "discounted_cash_price": "50000",
    }

    prices = prices_from_record(
        record,
        procedure_name="Hip replacement",
        procedure_code="470",
        code_type="DRG",
        source_url="https://example.org/mrf.json",
        last_updated="2026-01-01",
    )

    assert [(price.price_type, price.amount) for price in prices] == [
        ("gross", 100000.0),
        ("cash", 50000.0),
    ]


def test_prices_from_record_supports_2026_csv_price_columns() -> None:
    record = {
        "description": "Major joint replacement",
        "standard_charge|gross": "145426.90",
        "standard_charge|discounted_cash": "36356.72",
        "standard_charge|negotiated_dollar": "18689.88",
        "standard_charge|min": "16164.18",
        "standard_charge|max": "52946.38",
        "payer_name": "MEDICARE ADVANTAGE",
        "plan_name": "MEDICARE HMO/PPO",
    }

    prices = prices_from_record(
        record,
        procedure_name="Hip replacement",
        procedure_code="470",
        code_type="DRG",
        source_url="https://example.org/mrf.csv",
        last_updated="2026-01-01",
    )

    assert {price.price_type for price in prices} == {
        "gross",
        "cash",
        "negotiated",
        "negotiated_min",
        "negotiated_max",
    }


def test_prices_from_standard_charge_item_flattens_nested_charges() -> None:
    item = {
        "description": "Major joint replacement",
        "standard_charges": [
            {
                "minimum": 10000,
                "maximum": 40000,
                "gross_charge": 70000,
                "discounted_cash": 25000,
                "setting": "inpatient",
                "payers_information": [
                    {
                        "payer_name": "Aetna",
                        "plan_name": "PPO",
                        "standard_charge_dollar": 30000,
                        "count": "3",
                    }
                ],
            }
        ],
    }

    prices = prices_from_standard_charge_item(
        item,
        procedure_name="Hip replacement",
        procedure_code="470",
        code_type="DRG",
        source_url="https://example.org/mrf.json",
        last_updated="2026-01-01",
    )

    assert {price.price_type for price in prices} == {
        "gross",
        "cash",
        "negotiated_min",
        "negotiated_max",
        "negotiated",
    }
