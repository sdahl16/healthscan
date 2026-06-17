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
    price_details_help_text,
    price_selection_explanation,
    source_metadata,
)


def test_cash_rows_label_payer_plan_as_source_file_field() -> None:
    row = {"price_type": "cash", "payer_name": "MEDICARE ADVANTAGE [442]", "plan_name": "MEDICARE HMO/PPO"}

    assert display_payer_plan(row) == "Source file field: MEDICARE ADVANTAGE [442] / MEDICARE HMO/PPO"


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
    assert "cash/self-pay" in price_selection_explanation("cash")
    assert "negotiated" in price_selection_explanation("negotiated")
    assert "preferring cash/self-pay" in price_selection_explanation("all")


def test_price_details_help_text_explains_repeated_amounts() -> None:
    help_text = price_details_help_text()

    assert "same dollar amount" in help_text
    assert "different payer or plan" in help_text
    assert "exact duplicate" in help_text


def test_repeated_display_amounts_keep_distinct_payer_plan_context() -> None:
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
    repeated_112 = [row for row in prices if row["display_amount_group_count"] == 4]
    repeated_262 = [row for row in prices if row["display_amount_group_count"] == 2]

    assert len(repeated_112) == 4
    assert {row["payer_plan_display"] for row in repeated_112} == {
        "United Healthcare / United Healthcare - HMO",
        "Managed Health Network / MHN - Medicare",
        "Blue Cross / Blue Cross - Standard",
        "Blue Cross / Blue Cross - HMO",
    }
    assert len(repeated_262) == 2
    assert all("same displayed amount" in row["display_amount_note"] for row in repeated_112 + repeated_262)


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
