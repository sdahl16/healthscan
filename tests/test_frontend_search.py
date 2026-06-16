from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from frontend_search import display_payer_plan, price_selection_explanation, source_metadata


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
