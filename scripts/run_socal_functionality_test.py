from __future__ import annotations

import csv
import argparse
from pathlib import Path

from healthscan.search_query import search_prices


ROOT = Path(__file__).resolve().parents[1]
VALIDATION_PATH = ROOT / "data" / "reference" / "translation_validation_set.csv"
OUT_PATH = ROOT / "data" / "research" / "socal_functionality_results.csv"
SUMMARY_PATH = ROOT / "data" / "research" / "socal_functionality_summary.csv"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--search-results", type=Path, default=ROOT / "data" / "processed" / "layer3_search_results.csv")
    parser.add_argument("--output-suffix", default="")
    args = parser.parse_args()

    out_path = OUT_PATH
    summary_path = SUMMARY_PATH
    if args.output_suffix:
        out_path = OUT_PATH.with_name(f"{OUT_PATH.stem}_{args.output_suffix}{OUT_PATH.suffix}")
        summary_path = SUMMARY_PATH.with_name(f"{SUMMARY_PATH.stem}_{args.output_suffix}{SUMMARY_PATH.suffix}")

    exact_queries: list[str] = []
    with VALIDATION_PATH.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["case_type"] == "exact":
                exact_queries.append(row["input"])

    rows: list[dict[str, str]] = []
    for query in exact_queries:
        status, hits = search_prices(query, area="southern_california", path=args.search_results)
        rows.append(
            {
                "query": query,
                "status": status,
                "hit_count": str(len(hits)),
                "hospital_count": str(len({hit.hospital for hit in hits})),
                "min_price": str(min((hit.display_price for hit in hits), default="")),
                "top_hospital": hits[0].hospital if hits else "",
                "top_price": str(hits[0].display_price) if hits else "",
            }
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    supported = sum(1 for row in rows if row["status"] == "ok")
    three_plus = sum(1 for row in rows if int(row["hospital_count"]) >= 3)
    no_results = sum(1 for row in rows if row["status"] == "no_results")
    summary = {
        "queries": len(rows),
        "queries_with_results": supported,
        "queries_with_3plus_hospitals": three_plus,
        "queries_needing_indexing": no_results,
        "gate_scope": args.search_results.stem,
        "gate_result": "pass" if supported >= 10 and three_plus >= 10 else "needs_more_indexing",
    }
    with summary_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary))
        writer.writeheader()
        writer.writerow(summary)

    print(f"queries={summary['queries']}")
    print(f"queries_with_results={summary['queries_with_results']}")
    print(f"queries_with_3plus_hospitals={summary['queries_with_3plus_hospitals']}")
    print(f"queries_needing_indexing={summary['queries_needing_indexing']}")
    print(f"gate_scope={summary['gate_scope']}")
    print(f"gate_result={summary['gate_result']}")
    print(f"results={out_path}")
    print(f"summary={summary_path}")
    return 0 if summary["gate_result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
