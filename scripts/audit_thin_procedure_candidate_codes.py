from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "processed" / "healthscan.sqlite"
OUT_PATH = ROOT / "data" / "research" / "phase2_thin_procedure_baseline.csv"

PROCEDURES = [
    "MRI brain",
    "Colonoscopy",
    "Screening colonoscopy",
    "Emergency department visit",
    "Appendectomy",
    "Appendectomy (inpatient)",
    "C-section",
    "Vaginal delivery",
    "Hip replacement",
    "Knee replacement",
    "Cardiac catheterization",
]


def main() -> int:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    rows: list[dict[str, str]] = []
    for procedure in PROCEDURES:
        matches = connection.execute(
            """
            SELECT
                p.procedure_name,
                p.code_type,
                p.procedure_code,
                COUNT(*) AS rows,
                COUNT(DISTINCT p.hospital_id) AS hospitals,
                COUNT(DISTINCT CASE WHEN p.price_type = 'cash' THEN p.hospital_id END) AS cash_hospitals,
                COUNT(DISTINCT CASE WHEN p.price_type IN ('negotiated', 'negotiated_min') THEN p.hospital_id END) AS negotiated_hospitals
            FROM indexed_prices p
            WHERE p.procedure_name = ?
            GROUP BY p.procedure_name, p.code_type, p.procedure_code
            ORDER BY p.code_type, p.procedure_code
            """,
            (procedure,),
        ).fetchall()
        if not matches:
            rows.append(
                {
                    "procedure_name": procedure,
                    "code_type": "",
                    "procedure_code": "",
                    "rows": "0",
                    "hospitals": "0",
                    "cash_hospitals": "0",
                    "negotiated_hospitals": "0",
                }
            )
            continue
        rows.extend({key: str(match[key]) for key in match.keys()} for match in matches)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "procedure_name",
                "code_type",
                "procedure_code",
                "rows",
                "hospitals",
                "cash_hospitals",
                "negotiated_hospitals",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"rows={len(rows)}")
    print(f"output={OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
