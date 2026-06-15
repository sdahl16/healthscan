from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from scripts.migrate_combined_search_to_sqlite import migrate


def workspace_tmp_path(name: str) -> Path:
    path = Path("data") / "tmp" / "tests" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def test_migrate_combined_search_to_sqlite_loads_rows_and_relevance_columns() -> None:
    input_path = workspace_tmp_path("combined-migration.csv")
    db_path = workspace_tmp_path("combined-migration.sqlite")
    with input_path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "hospital",
            "procedure_name",
            "code_type",
            "code",
            "description",
            "setting",
            "display_price",
            "display_price_type",
            "payer_name",
            "plan_name",
            "data_quality_flag",
            "user_relevance_flag",
            "user_relevance_reason",
            "source_url",
            "evidence_source",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(
            {
                "hospital": "Example Hospital",
                "procedure_name": "EKG",
                "code_type": "CPT",
                "code": "93000",
                "description": "Electrocardiogram",
                "setting": "outpatient",
                "display_price": "125.00",
                "display_price_type": "cash",
                "payer_name": "",
                "plan_name": "",
                "data_quality_flag": "ok",
                "user_relevance_flag": "display_ok",
                "user_relevance_reason": "",
                "source_url": "https://example.org/standardcharges.csv",
                "evidence_source": "test",
            }
        )

    summary = migrate(input_path, db_path)

    assert summary["inserted_rows"] == 1
    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            "SELECT procedure_code, code_type, price_type, amount, user_relevance_flag FROM indexed_prices"
        ).fetchone()
    assert row == ("93000", "CPT", "cash", 125, "display_ok")
