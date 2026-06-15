from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path

from healthscan.layer4 import (
    coverage_for_targets,
    load_known_sources,
    load_search_ready_counts,
    load_targets,
    summarize_coverage,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "data" / "research" / "layer4_scan_engine_audit.csv"
SUMMARY_PATH = ROOT / "data" / "research" / "layer4_scan_engine_summary.csv"


def main() -> int:
    targets = load_targets()
    coverage = coverage_for_targets(
        targets,
        sources=load_known_sources(),
        search_counts=load_search_ready_counts(),
    )
    summary = summarize_coverage(coverage)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(coverage[0])))
        writer.writeheader()
        writer.writerows(asdict(row) for row in coverage)

    with SUMMARY_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary))
        writer.writeheader()
        writer.writerow(summary)

    print(f"targets={summary['target_hospitals']}")
    print(f"known_sources={summary['known_sources']}")
    print(f"search_ready_hospitals={summary['search_ready_hospitals']}")
    print(f"source_known_needs_indexing={summary['source_known_needs_indexing']}")
    print(f"needs_discovery={summary['needs_discovery']}")
    print(f"audit={OUT_PATH}")
    print(f"summary={SUMMARY_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
