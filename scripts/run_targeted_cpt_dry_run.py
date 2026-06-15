from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
from pathlib import Path

from healthscan.local_sources import resolve_local_source
from healthscan.search_export import SearchResult, search_result_from_record
from healthscan.streaming_json import records_from_large_json_file_for_codes
from run_layer4_local_scan_batch import scan_csv_group


ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "data" / "research" / "layer4_scan_engine_audit.csv"
OUT_PATH = ROOT / "data" / "research" / "targeted_cpt_dry_run_results.csv"
SEARCH_OUT_PATH = ROOT / "data" / "research" / "targeted_cpt_dry_run_search_rows.csv"
SUMMARY_PATH = ROOT / "data" / "research" / "targeted_cpt_dry_run_summary.csv"

TARGETS = [
    {"procedure_name": "CT scan abdomen", "code_type": "CPT", "procedure_code": "74178"},
    {"procedure_name": "Carpal tunnel surgery", "code_type": "CPT", "procedure_code": "64721"},
    {"procedure_name": "Knee arthroscopy", "code_type": "CPT", "procedure_code": "29881"},
    {"procedure_name": "MRI spine", "code_type": "CPT", "procedure_code": "72148"},
    {"procedure_name": "Shoulder arthroscopy", "code_type": "CPT", "procedure_code": "29827"},
]


def scan_json_group(
    matrix_rows: list[dict[str, str]],
    local_path: Path,
    *,
    max_matches_per_target: int | None,
) -> dict[int, list[dict[str, object]]]:
    records_by_target = records_from_large_json_file_for_codes(
        local_path,
        targets=[(row["code_type"], row["procedure_code"]) for row in matrix_rows],
        max_matches_per_target=max_matches_per_target,
    )
    matches: dict[int, list[dict[str, object]]] = {}
    for row in matrix_rows:
        target = (row["code_type"].upper(), row["procedure_code"])
        matches[int(row["_row_id"])] = records_by_target.get(target, [])
    return matches


def result_from_match(row: dict[str, str], record: dict[str, object]) -> SearchResult | None:
    return search_result_from_record(
        record,
        hospital=row["hospital_name"],
        procedure_name=row["procedure_name"],
        code_type=row["code_type"],
        code=row["procedure_code"],
        source_url=row["mrf_url"],
        evidence_source="targeted_cpt_dry_run",
    )


def build_matrix_rows() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    matrix_rows: list[dict[str, str]] = []
    skipped_rows: list[dict[str, str]] = []
    row_id = 0
    with AUDIT_PATH.open(newline="", encoding="utf-8") as handle:
        for hospital in csv.DictReader(handle):
            if hospital["engine_status"] not in {"search_ready", "source_known_needs_indexing"}:
                continue
            if not hospital["mrf_url"]:
                continue
            source = resolve_local_source(hospital["mrf_url"])
            for target in TARGETS:
                row = {
                    "hospital_name": hospital["hospital_name"],
                    "hospital_system": hospital["hospital_system"],
                    "region": hospital["region"],
                    "mrf_url": hospital["mrf_url"],
                    "hospital_engine_status": hospital["engine_status"],
                    **target,
                    "care_setting": "outpatient",
                    "scan_status": "queued",
                }
                if source is None:
                    skipped_rows.append(
                        {
                            **row,
                            "local_path": "",
                            "local_scan_status": "skipped_no_local_source",
                            "match_count": "0",
                            "search_ready_count": "0",
                            "scan_scope": "",
                        }
                    )
                    continue
                matrix_rows.append(
                    {
                        **row,
                        "_row_id": str(row_id),
                        "_local_path": str(source.path),
                        "_mrf_format": source.mrf_format,
                        "_scan_scope": source.scan_scope,
                    }
                )
                row_id += 1
    return matrix_rows, skipped_rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv-limit", type=int, default=None)
    parser.add_argument("--max-json-matches", type=int, default=None)
    args = parser.parse_args()

    matrix_rows, skipped_rows = build_matrix_rows()
    matches_by_row: dict[int, list[dict[str, object]]] = {}
    grouped: dict[tuple[str, str], list[dict[str, str]]] = {}
    for matrix_row in matrix_rows:
        grouped.setdefault((matrix_row["_local_path"], matrix_row["_mrf_format"]), []).append(matrix_row)

    for (local_path_text, mrf_format), group_rows in grouped.items():
        local_path = Path(local_path_text)
        if mrf_format == "csv":
            matches_by_row.update(scan_csv_group(group_rows, local_path, limit=args.csv_limit))
        elif mrf_format == "json":
            matches_by_row.update(
                scan_json_group(
                    group_rows,
                    local_path,
                    max_matches_per_target=args.max_json_matches,
                )
            )

    result_rows: list[dict[str, str]] = []
    search_results: list[SearchResult] = []
    for matrix_row in matrix_rows:
        matches = matches_by_row.get(int(matrix_row["_row_id"]), [])
        ready = [result for record in matches if (result := result_from_match(matrix_row, record))]
        search_results.extend(ready)
        result_rows.append(
            {
                **{key: value for key, value in matrix_row.items() if not key.startswith("_")},
                "local_path": matrix_row["_local_path"],
                "local_scan_status": "matched" if matches else "no_match",
                "match_count": str(len(matches)),
                "search_ready_count": str(len(ready)),
                "scan_scope": matrix_row["_scan_scope"],
            }
        )
    result_rows.extend(skipped_rows)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result_fieldnames = [
        "hospital_name",
        "hospital_system",
        "region",
        "mrf_url",
        "hospital_engine_status",
        "procedure_name",
        "code_type",
        "procedure_code",
        "care_setting",
        "scan_status",
        "local_path",
        "local_scan_status",
        "match_count",
        "search_ready_count",
        "scan_scope",
    ]
    with OUT_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=result_fieldnames)
        writer.writeheader()
        writer.writerows(result_rows)

    with SEARCH_OUT_PATH.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = list(asdict(search_results[0]).keys()) if search_results else list(SearchResult.__dataclass_fields__)
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(asdict(result) for result in search_results)

    summary_rows: list[dict[str, str]] = []
    for target in TARGETS:
        code_results = [result for result in search_results if result.code == target["procedure_code"]]
        display_results = [result for result in code_results if result.user_relevance_flag == "display_ok"]
        summary_rows.append(
            {
                "procedure_name": target["procedure_name"],
                "code_type": target["code_type"],
                "procedure_code": target["procedure_code"],
                "search_ready_rows": str(len(code_results)),
                "distinct_hospitals": str(len({result.hospital for result in code_results})),
                "display_rows": str(len(display_results)),
                "display_hospitals": str(len({result.hospital for result in display_results})),
                "matched_jobs": str(
                    sum(
                        1
                        for row in result_rows
                        if row["procedure_code"] == target["procedure_code"]
                        and row["local_scan_status"] == "matched"
                    )
                ),
            }
        )
    with SUMMARY_PATH.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = list(summary_rows[0])
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"scan_jobs={len(result_rows)}")
    print(f"local_scan_jobs={len(matrix_rows)}")
    print(f"skipped_no_local_source={len(skipped_rows)}")
    print(f"search_ready_rows={len(search_results)}")
    for row in summary_rows:
        print(
            f"{row['procedure_code']} rows={row['search_ready_rows']} "
            f"hospitals={row['distinct_hospitals']} "
            f"display_rows={row['display_rows']} display_hospitals={row['display_hospitals']}"
        )
    print(f"results={OUT_PATH}")
    print(f"search_rows={SEARCH_OUT_PATH}")
    print(f"summary={SUMMARY_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
