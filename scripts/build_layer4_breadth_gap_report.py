from __future__ import annotations

import csv
from pathlib import Path

from healthscan.relevance import assess_price_relevance


ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "data" / "research" / "socal_functionality_results_combined.csv"
SEARCH_RESULTS_PATH = ROOT / "data" / "processed" / "combined_search_results.csv"
LOCAL_SCAN_PATH = ROOT / "data" / "research" / "layer4_local_scan_results.csv"
OUT_PATH = ROOT / "data" / "research" / "layer4_breadth_gap.csv"
SUMMARY_PATH = ROOT / "data" / "research" / "layer4_breadth_gap_summary.csv"


def next_action(hospital_count: int) -> str:
    if hospital_count == 0:
        return "index matching rows from known sources"
    if hospital_count == 1:
        return "add two more hospital matches via full-MRF scans or source discovery"
    return "add one more hospital match via full-MRF scan or source discovery"


def main() -> int:
    with INPUT_PATH.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    with SEARCH_RESULTS_PATH.open(newline="", encoding="utf-8") as handle:
        search_rows = list(csv.DictReader(handle))
    with LOCAL_SCAN_PATH.open(newline="", encoding="utf-8") as handle:
        scan_rows = list(csv.DictReader(handle))

    gaps: list[dict[str, str]] = []
    for row in rows:
        hospital_count = int(row["hospital_count"])
        if hospital_count >= 3:
            continue
        needed = 3 - hospital_count
        current_hospitals = sorted(
            {
                search_row["hospital"]
                for search_row in search_rows
                if search_row["procedure_name"] == row["query"]
                and assess_price_relevance(search_row).is_user_relevant
            }
        )
        unmatched_local_hospitals = sorted(
            {
                scan_row["hospital_name"]
                for scan_row in scan_rows
                if scan_row["procedure_name"] == row["query"]
                and scan_row["local_scan_status"] == "no_match"
                and scan_row["hospital_name"] not in current_hospitals
            }
        )
        gaps.append(
            {
                "query": row["query"],
                "status": row["status"],
                "hit_count": row["hit_count"],
                "hospital_count": row["hospital_count"],
                "needed_hospitals": str(needed),
                "current_hospitals": "; ".join(current_hospitals),
                "unmatched_local_hospitals": "; ".join(unmatched_local_hospitals),
                "next_action": next_action(hospital_count),
            }
        )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "query",
            "status",
            "hit_count",
            "hospital_count",
            "needed_hospitals",
            "current_hospitals",
            "unmatched_local_hospitals",
            "next_action",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(gaps)

    summary = {
        "total_queries": str(len(rows)),
        "queries_with_3plus_hospitals": str(len(rows) - len(gaps)),
        "queries_below_breadth_target": str(len(gaps)),
        "additional_hospital_matches_needed": str(sum(int(row["needed_hospitals"]) for row in gaps)),
        "output": str(OUT_PATH),
    }
    with SUMMARY_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary))
        writer.writeheader()
        writer.writerow(summary)

    for key, value in summary.items():
        print(f"{key}={value}")
    print(f"summary={SUMMARY_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
