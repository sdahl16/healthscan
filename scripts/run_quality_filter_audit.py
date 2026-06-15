from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

from healthscan.relevance import assess_price_relevance


ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "data" / "processed" / "combined_search_results.csv"
SUMMARY_PATH = ROOT / "data" / "research" / "quality_filter_summary.csv"
DETAIL_PATH = ROOT / "data" / "research" / "quality_filter_by_procedure.csv"


def main() -> int:
    with INPUT_PATH.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    flag_counts: Counter[str] = Counter()
    procedure_totals: dict[str, Counter[str]] = {}
    for row in rows:
        assessment = assess_price_relevance(row)
        flag_counts[assessment.user_relevance_flag] += 1
        procedure_totals.setdefault(row["procedure_name"], Counter())[assessment.user_relevance_flag] += 1

    display_rows = flag_counts["display_ok"]
    filtered_rows = len(rows) - display_rows
    summary = {
        "total_rows": str(len(rows)),
        "display_rows": str(display_rows),
        "filtered_rows": str(filtered_rows),
        "display_percent": f"{(display_rows / len(rows) * 100):.1f}" if rows else "0.0",
        "filtered_percent": f"{(filtered_rows / len(rows) * 100):.1f}" if rows else "0.0",
        "flag_counts": "; ".join(f"{flag}={count}" for flag, count in sorted(flag_counts.items())),
    }

    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SUMMARY_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary))
        writer.writeheader()
        writer.writerow(summary)

    with DETAIL_PATH.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = ["procedure_name", "total_rows", "display_rows", "filtered_rows", "filtered_flags"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for procedure_name in sorted(procedure_totals):
            counts = procedure_totals[procedure_name]
            total = sum(counts.values())
            display = counts["display_ok"]
            filtered = total - display
            writer.writerow(
                {
                    "procedure_name": procedure_name,
                    "total_rows": total,
                    "display_rows": display,
                    "filtered_rows": filtered,
                    "filtered_flags": "; ".join(
                        f"{flag}={count}"
                        for flag, count in sorted(counts.items())
                        if flag != "display_ok"
                    ),
                }
            )

    for key, value in summary.items():
        print(f"{key}={value}")
    print(f"summary={SUMMARY_PATH}")
    print(f"detail={DETAIL_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
