from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Any

from healthscan.indexer import _codes_from_record
from healthscan.local_sources import resolve_local_source
from healthscan.search_export import SearchResult, search_results_from_record
from healthscan.streaming_json import records_from_large_json_file_for_codes

ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "data" / "research" / "layer4_scan_matrix.csv"
OUT_PATH = ROOT / "data" / "processed" / "layer4_local_search_results.csv"
AUDIT_PATH = ROOT / "data" / "research" / "layer4_fast_price_type_reindex_audit.csv"


def charge_header(row: list[str]) -> bool:
    normalized = {column.strip().lower().replace(" ", "_").replace("-", "_") for column in row}
    return "description" in normalized and any(column.startswith("code|") for column in row)


def normalized_type(value: str) -> str:
    return value.replace("-", "").upper()


def types_match(wanted_type: str, found_type: str) -> bool:
    wanted = normalized_type(wanted_type)
    found = normalized_type(found_type)
    return found == wanted or (wanted == "DRG" and found in {"MSDRG"}) or (wanted == "CPT" and found == "HCPCS")


def matching_rows(record: dict[str, Any], targets_by_code: dict[str, list[dict[str, str]]]) -> list[dict[str, str]]:
    matches: list[dict[str, str]] = []
    seen: set[int] = set()
    for found_type, found_code in _codes_from_record(record):
        for row in targets_by_code.get(found_code, []):
            if int(row["_row_id"]) in seen:
                continue
            if types_match(row["code_type"], found_type):
                seen.add(int(row["_row_id"]))
                matches.append(row)
    return matches


def scan_csv_fast(path: Path, rows: list[dict[str, str]]) -> tuple[list[tuple[dict[str, str], dict[str, Any]]], int]:
    targets_by_code: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        targets_by_code[row["procedure_code"]].append(row)
    target_codes = tuple(sorted(targets_by_code, key=len, reverse=True))
    target_pattern = re.compile("|".join(re.escape(code) for code in target_codes))
    raw_matches = 0
    matched: list[tuple[dict[str, str], dict[str, Any]]] = []
    last_error: UnicodeDecodeError | None = None
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            with path.open(newline="", encoding=encoding) as handle:
                reader = csv.reader(handle)
                header = None
                for raw_row in reader:
                    if charge_header(raw_row):
                        header = raw_row
                        break
                if header is None:
                    return [], 0
                for line in handle:
                    if not target_pattern.search(line):
                        continue
                    record = None
                    for values in csv.reader([line]):
                        record = {field: values[index] if index < len(values) else "" for index, field in enumerate(header)}
                    if record is None:
                        continue
                    record_matches = matching_rows(record, targets_by_code)
                    if record_matches:
                        raw_matches += 1
                        for row in record_matches:
                            matched.append((row, record))
            return matched, raw_matches
        except UnicodeDecodeError as error:
            last_error = error
            continue
    if last_error is not None:
        raise last_error
    return [], 0


def scan_json(path: Path, rows: list[dict[str, str]], max_matches_per_target: int | None) -> tuple[list[tuple[dict[str, str], dict[str, Any]]], int]:
    targets = [(row["code_type"], row["procedure_code"]) for row in rows]
    records_by_target = records_from_large_json_file_for_codes(path, targets=targets, max_matches_per_target=max_matches_per_target)
    matched: list[tuple[dict[str, str], dict[str, Any]]] = []
    raw_matches = 0
    for row in rows:
        target = (row["code_type"].upper(), row["procedure_code"])
        records = records_by_target.get(target, [])
        raw_matches += len(records)
        matched.extend((row, record) for record in records)
    return matched, raw_matches


def load_matrix(include_alternates: bool) -> list[dict[str, str]]:
    matrix_rows: list[dict[str, str]] = []
    with MATRIX_PATH.open(newline="", encoding="utf-8") as handle:
        for row_id, matrix_row in enumerate(csv.DictReader(handle)):
            if not include_alternates and matrix_row["is_primary"] != "true":
                continue
            source = resolve_local_source(matrix_row["mrf_url"])
            if source is None:
                continue
            matrix_rows.append(
                {
                    **matrix_row,
                    "_row_id": str(row_id),
                    "_local_path": str(source.path),
                    "_mrf_format": source.mrf_format,
                }
            )
    return matrix_rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--include-alternates", action="store_true")
    parser.add_argument("--max-json-matches", type=int, default=10000)
    parser.add_argument("--only-file", action="append", default=[])
    parser.add_argument("--output", type=Path, default=OUT_PATH)
    parser.add_argument("--audit-output", type=Path, default=AUDIT_PATH)
    args = parser.parse_args()

    matrix_rows = load_matrix(args.include_alternates)
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in matrix_rows:
        if args.only_file and Path(row["_local_path"]).name not in set(args.only_file):
            continue
        grouped[(row["_local_path"], row["_mrf_format"])].append(row)

    results: list[SearchResult] = []
    audit_rows: list[dict[str, str]] = []
    for (path_text, mrf_format), rows in grouped.items():
        path = Path(path_text)
        print(f"scanning {path.name} ({mrf_format})", flush=True)
        if mrf_format == "csv":
            matched, raw_matches = scan_csv_fast(path, rows)
        else:
            matched, raw_matches = scan_json(path, rows, args.max_json_matches)
        before = len(results)
        for row, record in matched:
            results.extend(
                search_results_from_record(
                    record,
                    hospital=row["hospital_name"],
                    procedure_name=row["procedure_name"],
                    code_type=row["code_type"],
                    code=row["procedure_code"],
                    source_url=row["mrf_url"],
                    evidence_source="layer4_fast_price_type_reindex",
                )
            )
        audit_rows.append(
            {
                "file": path.name,
                "format": mrf_format,
                "jobs": str(len(rows)),
                "raw_matches": str(raw_matches),
                "search_ready_rows": str(len(results) - before),
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = list(asdict(results[0]).keys()) if results else list(SearchResult.__dataclass_fields__)
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(asdict(result) for result in results)

    args.audit_output.parent.mkdir(parents=True, exist_ok=True)
    with args.audit_output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["file", "format", "jobs", "raw_matches", "search_ready_rows"])
        writer.writeheader()
        writer.writerows(audit_rows)

    print(f"search_ready_rows={len(results)}")
    print(f"output={args.output}")
    print(f"audit={args.audit_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
