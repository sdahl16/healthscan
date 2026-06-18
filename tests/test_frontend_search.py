from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from frontend_search import (
    HOSPITAL_COORDS,
    HOSPITAL_METADATA,
    Location,
    build_hospitals,
    display_payer_plan,
    insurance_filter_options,
    no_results_message,
    price_details_help_text,
    price_range_summary,
    price_selection_explanation,
    search,
    source_metadata,
    summarize_payer_plans,
    unavailable_message,
    user_testing_prompts,
)


def test_cash_rows_label_payer_plan_as_source_file_field() -> None:
    row = {"price_type": "cash", "payer_name": "MEDICARE ADVANTAGE [442]", "plan_name": "MEDICARE HMO/PPO"}

    assert display_payer_plan(row) == "Source file field: MEDICARE ADVANTAGE [442] / MEDICARE HMO/PPO"


def test_cash_rows_without_payer_plan_display_as_self_pay() -> None:
    row = {"price_type": "cash", "payer_name": None, "plan_name": None}

    assert display_payer_plan(row) == "Cash / self-pay"


def test_negotiated_rows_keep_payer_plan_display() -> None:
    row = {"price_type": "negotiated", "payer_name": "Aetna", "plan_name": "PPO"}

    assert display_payer_plan(row) == "Aetna / PPO"


def test_source_metadata_prefers_hospital_file_date_over_index_timestamp() -> None:
    row = {"last_updated": "2026-04-01", "parsed_at": "2026-06-15 20:26:29", "source_url": "https://example.org/mrf.json"}

    assert source_metadata(row) == {
        "url": "https://example.org/mrf.json",
        "hospital_file_date": "2026-04-01",
        "indexed_at": "2026-06-15 20:26:29",
        "timestamp_label": "Hospital file date",
        "display_timestamp": "2026-04-01",
    }


def test_price_selection_explanation_changes_by_filter() -> None:
    assert "self-pay" in price_selection_explanation("cash")
    assert "Have insurance?" in price_selection_explanation("cash")
    assert "negotiated" in price_selection_explanation("negotiated")
    assert "mixes self-pay prices and payer-specific negotiated rates" in price_selection_explanation("all")


def test_default_search_uses_self_pay_prices_for_patient_friendly_start() -> None:
    result = search({"procedure": "echocardiogram", "location": "San Diego", "radius": 100})

    assert result["price_filter"] == "cash"
    assert result["price_filter_label"] == "Self-pay prices"
    assert result["hospitals"]
    assert all(hospital["headline_price"]["type"] == "cash" for hospital in result["hospitals"])


def test_advanced_all_prices_summary_keeps_cash_and_negotiated_ranges_separate() -> None:
    result = search({"procedure": "echocardiogram", "location": "San Diego", "radius": 100, "priceType": "all"})

    assert result["price_filter_label"] == "All prices — advanced"
    assert result["price_ranges"]["cash"] == {"label": "Self-pay range", "min": 1356.0, "max": 6685.0}
    assert result["price_ranges"]["negotiated"] == {"label": "Insurance negotiated range", "min": 125.35, "max": 1798.52}


def test_price_range_summary_splits_self_pay_and_negotiated_ranges() -> None:
    hospitals = [
        {"headline_price": {"type": "negotiated", "amount": 125.35}},
        {"headline_price": {"type": "negotiated", "amount": 1798.52}},
        {"headline_price": {"type": "cash", "amount": 1356.0}},
        {"headline_price": {"type": "cash", "amount": 6685.0}},
    ]

    assert price_range_summary(hospitals) == {
        "cash": {"label": "Self-pay range", "min": 1356.0, "max": 6685.0},
        "negotiated": {"label": "Insurance negotiated range", "min": 125.35, "max": 1798.52},
    }


def test_price_details_help_text_explains_repeated_amounts() -> None:
    help_text = price_details_help_text()

    assert "same dollar amount" in help_text
    assert "different payer or plan" in help_text
    assert "exact duplicate" in help_text


def test_alpha_empty_state_messages_explain_next_steps() -> None:
    unavailable = unavailable_message()
    no_results = no_results_message()

    assert "recognized" in unavailable
    assert "not broken" in unavailable
    assert "Try one of the supported examples" in unavailable
    assert "price filter" in no_results
    assert "Expand the radius" in no_results
    assert "selected Southern California hospitals" in no_results


def test_user_testing_prompts_capture_trust_confusion_and_source_feedback() -> None:
    prompts = user_testing_prompts()

    assert len(prompts) >= 5
    joined = " ".join(prompts).lower()
    assert "trust" in joined
    assert "source" in joined
    assert "confusing" in joined


def test_repeated_display_amounts_collapse_to_distinct_amount_rows() -> None:
    rows = [
        {
            "hospital_id": 1,
            "hospital_name": "Sharp Chula Vista Medical Center",
            "address": "751 Medical Center Ct, Chula Vista, CA 91911",
            "state": "CA",
            "zip": "91911",
            "procedure_name": "MRI spine",
            "procedure_code": "72148",
            "code_type": "CPT",
            "description": "MRI lumbar spine",
            "setting": "outpatient",
            "price_type": "negotiated",
            "amount": amount,
            "payer_name": payer,
            "plan_name": plan,
            "last_updated": None,
            "source_url": "https://example.org/sharp.csv",
            "data_quality_flag": "ok",
            "parsed_at": "2026-06-17 18:36:36",
        }
        for amount, payer, plan in [
            (111.88, "United Healthcare", "United Healthcare - HMO"),
            (111.88, "Managed Health Network", "MHN - Medicare"),
            (111.88, "Blue Cross", "Blue Cross - Standard"),
            (111.88, "Blue Cross", "Blue Cross - HMO"),
            (262.22, "Blue Cross", "Blue Cross - PPO"),
            (262.22, "County Medical Services", "County of San Diego"),
        ]
    ]

    hospitals, _ = build_hospitals(rows, Location(32.6180, -117.0347, "Chula Vista, CA 91911", "local"), 25, "negotiated", "price")

    prices = hospitals[0]["prices"]

    assert len(prices) == 2
    assert prices[0]["display_amount_group_count"] == 4
    assert prices[0]["payer_plan_display"] == (
        "4 payer/plans: United Healthcare / United Healthcare - HMO; "
        "Managed Health Network / MHN - Medicare; Blue Cross / Blue Cross - Standard; +1 more"
    )
    assert prices[1]["display_amount_group_count"] == 2
    assert prices[1]["payer_plan_display"] == "2 payer/plans: Blue Cross / Blue Cross - PPO; County Medical Services / County of San Diego"
    assert all("same displayed amount" in row["display_amount_note"] for row in prices)


def test_repeated_display_amounts_without_payer_plan_collapse_to_unlisted_summary() -> None:
    rows = [
        {
            "price_type": "negotiated",
            "amount": amount,
            "payer_name": None,
            "plan_name": None,
        }
        for amount in [2968.1, 2968.2, 2968.3]
    ]

    assert summarize_payer_plans(rows) == "3 source rows; payer/plan not listed"


def hoag_blue_shield_rows() -> list[dict[str, object]]:
    base = {
        "hospital_id": 13,
        "hospital_name": "Hoag Hospital Newport Beach",
        "address": None,
        "state": "CA",
        "zip": "92663",
        "procedure_name": "Gallbladder removal",
        "procedure_code": "47562",
        "code_type": "CPT",
        "description": "Laparoscopic cholecystectomy",
        "setting": "outpatient",
        "price_type": "negotiated",
        "last_updated": None,
        "source_url": "https://example.org/hoag.csv",
        "data_quality_flag": "ok",
        "parsed_at": "2026-06-17 18:36:28",
    }
    return [
        {**base, "amount": 7775.56, "payer_name": "Aetna", "plan_name": "Medicare Managed Care Plan"},
        {**base, "amount": 11947.77, "payer_name": "Blue Shield", "plan_name": "Epn/Ifp Other Commercial Plan"},
        {**base, "amount": 12534.49, "payer_name": "Blue Shield", "plan_name": "Hmo/Pos"},
        {**base, "amount": 15350.75, "payer_name": "Blue Shield", "plan_name": "Ppo/Epo"},
        {**base, "amount": 27754.00, "payer_name": "Unitedhealthcare", "plan_name": "All Commercial Plans"},
    ]


def test_insurance_filter_options_are_built_from_available_payers() -> None:
    options = insurance_filter_options(hoag_blue_shield_rows())

    assert options == [
        {"value": "Aetna", "label": "Aetna", "count": 1},
        {"value": "Blue Shield", "label": "Blue Shield", "count": 3},
        {"value": "UnitedHealthcare", "label": "UnitedHealthcare", "count": 1},
    ]


def test_insurance_filter_options_group_source_file_variants_under_common_payers() -> None:
    rows = [
        {"price_type": "negotiated", "payer_name": "ALTERNATE BLUE SHIELD [2002]", "plan_name": "PPO"},
        {"price_type": "negotiated", "payer_name": "Blue Shield", "plan_name": "Hmo/Pos"},
        {"price_type": "negotiated", "payer_name": "BLUE SHIELD PROMISE [445]", "plan_name": "Medicaid"},
        {"price_type": "negotiated", "payer_name": "ANTHEM BLUE CROSS [1005]", "plan_name": "PPO"},
        {"price_type": "negotiated", "payer_name": "ADMAR [1001]", "plan_name": "PPO"},
    ]

    assert insurance_filter_options(rows) == [
        {"value": "Anthem Blue Cross", "label": "Anthem Blue Cross", "count": 1},
        {"value": "Blue Shield", "label": "Blue Shield", "count": 3},
        {"value": "ADMAR [1001]", "label": "ADMAR [1001]", "count": 1},
    ]


def test_insurance_filter_limits_prices_and_headline_to_matching_payer() -> None:
    hospitals, _ = build_hospitals(
        hoag_blue_shield_rows(),
        Location(33.6221, -117.9333, "Newport Beach, CA", "local"),
        25,
        "negotiated",
        "price",
        "Blue Shield",
    )

    assert len(hospitals) == 1
    hoag = hospitals[0]
    assert hoag["headline_price"]["payer_plan_display"] == "Blue Shield / Epn/Ifp Other Commercial Plan"
    assert [price["payer_plan_display"] for price in hoag["prices"]] == [
        "Blue Shield / Epn/Ifp Other Commercial Plan",
        "Blue Shield / Hmo/Pos",
        "Blue Shield / Ppo/Epo",
    ]
    assert "insurance filter: Blue Shield" in hoag["selection_explanation"]


def test_next_ten_hospitals_have_frontend_location_metadata() -> None:
    new_hospitals = {
        "Hollywood Presbyterian Medical Center",
        "Huntington Hospital",
        "UCI Medical Center",
        "Hoag Hospital Newport Beach",
        "MemorialCare Orange Coast Medical Center",
        "Loma Linda University Medical Center",
        "Riverside Community Hospital",
        "Tri-City Medical Center",
        "Los Robles Regional Medical Center",
        "Community Memorial Healthcare - Ventura",
    }

    assert new_hospitals <= set(HOSPITAL_COORDS)
    assert new_hospitals <= set(HOSPITAL_METADATA)
    assert HOSPITAL_METADATA["Cedars-Sinai Medical Center"]["address"]
    for hospital in new_hospitals:
        assert HOSPITAL_METADATA[hospital]["address"]
        assert HOSPITAL_METADATA[hospital]["state"] == "CA"
        assert HOSPITAL_METADATA[hospital]["zip"]
