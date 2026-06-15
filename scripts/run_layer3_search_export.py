from __future__ import annotations

import csv
from dataclasses import asdict, replace
from pathlib import Path

from healthscan.database import connect
from healthscan.search_export import (
    SearchResult,
    best_results_from_indexed_prices,
    dedupe_results,
    record_from_csv_sample,
    record_from_dict_sample,
    records_from_json_fragment,
    records_from_providence_snippet,
    search_result_from_record,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "data" / "processed" / "layer3_search_results.csv"
SUMMARY_PATH = ROOT / "data" / "research" / "mvp_layer3_gate_summary.csv"

CSV_SAMPLE_FILES = [
    ROOT / "data" / "research" / "mvp_layer2_csv_offsets.csv",
    ROOT / "data" / "research" / "mvp_layer2_alternate_offsets.csv",
]

DICT_SAMPLE_FILES = [
    ROOT / "data" / "research" / "mvp_layer2_rady_offsets.csv",
]

PROVIDENCE_FILES = [
    ROOT / "data" / "research" / "mvp_layer2_providence_offsets.csv",
    ROOT / "data" / "research" / "mvp_layer2_providence_alternate_offsets.csv",
]

JSON_FRAGMENT_FILES = [
    ROOT / "data" / "research" / "mvp_layer2_ucsd_offsets.csv",
]


def load_csv_sample_results(path: Path) -> list[SearchResult]:
    results: list[SearchResult] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            record = record_from_csv_sample(row["sample_line"])
            result = search_result_from_record(
                record,
                hospital=row["hospital"],
                procedure_name=row["procedure_name"],
                code_type=row["code_type"],
                code=row["code"],
                source_url=None,
                evidence_source=path.name,
            )
            if result:
                results.append(result)
    return results


def load_dict_sample_results(path: Path) -> list[SearchResult]:
    results: list[SearchResult] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            record = record_from_dict_sample(row["sample_line"])
            result = search_result_from_record(
                record,
                hospital=row["hospital"],
                procedure_name=row["procedure_name"],
                code_type=row["code_type"],
                code=row["code"],
                source_url=row["source_url"],
                evidence_source=path.name,
            )
            if result:
                results.append(result)
    return results


def load_providence_results(path: Path) -> list[SearchResult]:
    results: list[SearchResult] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            for record in records_from_providence_snippet(row["sample_text"]):
                result = search_result_from_record(
                    record,
                    hospital=row["hospital"],
                    procedure_name=row["procedure_name"],
                    code_type=row["code_type"],
                    code=row["code"],
                    source_url=row["source_url"],
                    evidence_source=path.name,
                )
                if result:
                    results.append(result)
    return results


def load_json_fragment_results(path: Path) -> list[SearchResult]:
    results: list[SearchResult] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            for record in records_from_json_fragment(row["sample_text"]):
                result = search_result_from_record(
                    record,
                    hospital=row["hospital"],
                    procedure_name=row["procedure_name"],
                    code_type=row["code_type"],
                    code=row["code"],
                    source_url=None,
                    evidence_source=path.name,
                )
                if result:
                    results.append(result)
    return results


def write_results(results: list[SearchResult]) -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = list(asdict(results[0]).keys()) if results else list(SearchResult.__dataclass_fields__)
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(asdict(result) for result in results)


def write_summary(results: list[SearchResult]) -> None:
    by_procedure: dict[str, set[str]] = {}
    for result in results:
        by_procedure.setdefault(result.procedure_name, set()).add(result.hospital)

    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SUMMARY_PATH.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = ["procedure_name", "search_ready_hospitals", "gate_result", "hospitals"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for procedure_name in sorted(by_procedure):
            hospitals = sorted(by_procedure[procedure_name])
            writer.writerow(
                {
                    "procedure_name": procedure_name,
                    "search_ready_hospitals": len(hospitals),
                    "gate_result": "pass" if len(hospitals) >= 3 else "needs_full_indexing",
                    "hospitals": "; ".join(hospitals),
                }
            )


def add_knee_replacement_alias(results: list[SearchResult]) -> list[SearchResult]:
    aliased = list(results)
    existing = {(result.hospital, result.procedure_name) for result in results}
    for result in results:
        if result.procedure_name != "Hip replacement" or result.code_type.upper() != "DRG" or result.code != "470":
            continue
        key = (result.hospital, "Knee replacement")
        if key in existing:
            continue
        aliased.append(replace(result, procedure_name="Knee replacement", evidence_source=f"{result.evidence_source}; drg_470_alias"))
        existing.add(key)
    return aliased


def main() -> None:
    with connect() as connection:
        results = best_results_from_indexed_prices(connection)

    for path in CSV_SAMPLE_FILES:
        results.extend(load_csv_sample_results(path))
    for path in DICT_SAMPLE_FILES:
        results.extend(load_dict_sample_results(path))
    for path in PROVIDENCE_FILES:
        results.extend(load_providence_results(path))
    for path in JSON_FRAGMENT_FILES:
        results.extend(load_json_fragment_results(path))

    deduped = dedupe_results(add_knee_replacement_alias(results))
    write_results(deduped)
    write_summary(deduped)

    passing = sum(1 for row in csv.DictReader(SUMMARY_PATH.open(encoding="utf-8")) if row["gate_result"] == "pass")
    print(f"search_ready_rows={len(deduped)} output={OUT_PATH}")
    print(f"procedures_with_3plus_search_ready_hospitals={passing}")
    print(f"summary={SUMMARY_PATH}")


if __name__ == "__main__":
    main()
