from __future__ import annotations

import csv
from pathlib import Path

from frontend_search import search

ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "data" / "research" / "phase2_thin_frontend_validation.csv"
PROCEDURES = [
    "MRI brain",
    "Colonoscopy",
    "Screening colonoscopy",
    "Emergency department visit",
    "Appendectomy",
    "C-section",
    "Vaginal delivery",
    "Hip replacement",
    "Knee replacement",
    "Cardiac catheterization",
]
LOCATIONS = ["San Diego", "Chula Vista", "La Jolla"]
PRICE_TYPES = ["cash", "negotiated", "all"]


def main() -> int:
    rows: list[dict[str, str]] = []
    for location in LOCATIONS:
        for procedure in PROCEDURES:
            for price_type in PRICE_TYPES:
                result = search(
                    {
                        "procedure": procedure,
                        "location": location,
                        "radius": 100,
                        "priceType": price_type,
                    }
                )
                availability = result.get("price_availability") or {}
                rows.append(
                    {
                        "location": location,
                        "procedure": procedure,
                        "price_type": price_type,
                        "status": str(result.get("status")),
                        "shown_hospitals": str(len(result.get("hospitals") or [])),
                        "self_pay_hospitals": str(availability.get("self_pay_hospitals", "")),
                        "negotiated_hospitals": str(availability.get("negotiated_hospitals", "")),
                        "any_price_hospitals": str(availability.get("any_price_hospitals", "")),
                        "total_indexed_hospitals": str(result.get("total_indexed_hospitals", "")),
                    }
                )
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"rows={len(rows)}")
    print(f"output={OUT_PATH}")
    for row in rows:
        if row["location"] == "San Diego" and row["price_type"] == "all":
            print(
                f"{row['procedure']}: status={row['status']} shown={row['shown_hospitals']} "
                f"availability={row['self_pay_hospitals']}/{row['negotiated_hospitals']}/{row['any_price_hospitals']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
