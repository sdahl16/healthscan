from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
from pathlib import Path

from healthscan.indexer import _codes_from_record
from healthscan.local_sources import resolve_local_source
from healthscan.search_export import SearchResult, search_results_from_record
from healthscan.streaming_json import records_from_large_json_file_for_codes


ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "data" / "research" / "layer4_scan_matrix.csv"
OUT_PATH = ROOT / "data" / "research" / "layer4_local_scan_results.csv"
SEARCH_OUT_PATH = ROOT / "data" / "processed" / "layer4_local_search_results.csv"


def charge_header(row: list[str]) -> bool:
    normalized = {column.strip().lower().replace(" ", "_").replace("-", "_") for column in row}
    return "description" in normalized and any(column.startswith("code|") for column in row)


def scan_csv_group(
    matrix_rows: list[dict[str, str]],
    local_path: Path,
    *,
    limit: int | None,
) -> dict[int, list[dict[str, object]]]:
    matches: dict[int, list[dict[str, object]]] = {int(row["_row_id"]): [] for row in matrix_rows}
    targets_by_code: dict[str, list[dict[str, str]]] = {}
    for matrix_row in matrix_rows:
        targets_by_code.setdefault(matrix_row["procedure_code"], []).append(matrix_row)

    last_decode_error: UnicodeDecodeError | None = None
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            with local_path.open(newline="", encoding=encoding) as handle:
                reader = csv.reader(handle)
                header = None
                for raw_row in reader:
                    if charge_header(raw_row):
                        header = raw_row
                        break
                if header is None:
                    return matches
                dict_reader = csv.DictReader(handle, fieldnames=header)
                for index, record in enumerate(dict_reader):
                    if limit is not None and index >= limit:
                        break
                    for found_type, found_code in _codes_from_record(record):
                        for matrix_row in targets_by_code.get(found_code, []):
                            wanted_type = matrix_row["code_type"].upper()
                            normalized_found_type = found_type.replace("-", "")
                            normalized_wanted_type = wanted_type.replace("-", "")
                            type_matches = normalized_found_type == normalized_wanted_type
                            if wanted_type == "DRG" and found_type in {"MS-DRG", "MSDRG"}:
                                type_matches = True
                            if wanted_type == "CPT" and found_type == "HCPCS":
                                type_matches = True
                            if type_matches:
                                matches[int(matrix_row["_row_id"])].append(record)
                return matches
        except UnicodeDecodeError as error:
            last_decode_error = error
            continue
    if last_decode_error is not None:
        raise last_decode_error
    return matches


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


def results_from_match(row: dict[str, str], record: dict[str, object]) -> list[SearchResult]:
    return search_results_from_record(
        record,
        hospital=row["hospital_name"],
        procedure_name=row["procedure_name"],
        code_type=row["code_type"],
        code=row["procedure_code"],
        source_url=row["mrf_url"],
        evidence_source="layer4_local_scan_batch",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--include-alternates", action="store_true")
    parser.add_argument("--include-large-json", action="store_true")
    parser.add_argument("--csv-limit", type=int, default=None)
    parser.add_argument("--max-json-matches", type=int, default=1)
    args = parser.parse_args()

    matrix_rows: list[dict[str, str]] = []
    skipped_rows: list[dict[str, str]] = []
    search_results: list[SearchResult] = []
    with MATRIX_PATH.open(newline="", encoding="utf-8") as handle:
        for row_id, matrix_row in enumerate(csv.DictReader(handle)):
            if not args.include_alternates and matrix_row["is_primary"] != "true":
                continue
            source = resolve_local_source(matrix_row["mrf_url"])
            if source is None:
                continue
            matrix_row = {**matrix_row, "_row_id": str(row_id), "_local_path": str(source.path), "_mrf_format": source.mrf_format, "_scan_scope": source.scan_scope}
            if source.mrf_format == "json" and source.scan_scope == "large_local_json" and not args.include_large_json:
                skipped_rows.append(
                    {
                        **matrix_row,
                        "local_path": str(source.path),
                        "local_scan_status": "skipped_large_json",
                        "match_count": "0",
                        "search_ready_count": "0",
                        "scan_scope": source.scan_scope,
                    }
                )
                continue
            matrix_rows.append(matrix_row)

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

    rows: list[dict[str, str]] = []
    for matrix_row in matrix_rows:
        matches = matches_by_row.get(int(matrix_row["_row_id"]), [])
        ready = [
            result
            for record in matches
            for result in results_from_match(matrix_row, record)
        ]
        search_results.extend(ready)
        rows.append(
            {
                **matrix_row,
                "local_path": matrix_row["_local_path"],
                "local_scan_status": "matched" if matches else "no_match",
                "match_count": str(len(matches)),
                "search_ready_count": str(len(ready)),
                "scan_scope": matrix_row["_scan_scope"],
            }
        )
    rows.extend(skipped_rows)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            *[
                "hospital_name",
                "hospital_system",
                "region",
                "mrf_url",
                "hospital_engine_status",
                "procedure_name",
                "code_type",
                "procedure_code",
                "care_setting",
                "is_primary",
                "scan_priority",
                "scan_status",
            ],
            "local_path",
            "local_scan_status",
            "match_count",
            "search_ready_count",
            "scan_scope",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        clean_rows = [
            {key: value for key, value in row.items() if not key.startswith("_")}
            for row in rows
        ]
        writer.writerows(clean_rows)

    SEARCH_OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SEARCH_OUT_PATH.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = list(asdict(search_results[0]).keys()) if search_results else list(SearchResult.__dataclass_fields__)
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(asdict(result) for result in search_results)

    matched_jobs = sum(1 for row in rows if row["local_scan_status"] == "matched")
    print(f"local_jobs={len(rows)}")
    print(f"matched_jobs={matched_jobs}")
    print(f"search_ready_rows={len(search_results)}")
    print(f"results={OUT_PATH}")
    print(f"search_results={SEARCH_OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
