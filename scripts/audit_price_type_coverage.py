from __future__ import annotations

import csv
import json
import sqlite3
import time
from collections import Counter
from pathlib import Path
from typing import Any

from healthscan.local_sources import LOCAL_MRF_SOURCES
from healthscan.indexer import _codes_from_record, parse_amount
from healthscan.search_export import search_result_from_record
from healthscan.streaming_json import records_from_large_json_file_for_codes

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "processed" / "healthscan.sqlite"
OUT = ROOT / "data" / "research" / "price_type_raw_audit_ekg.json"
TARGET_CODES = {"93000", "93005"}


def amount_present(record: dict[str, Any], key: str) -> bool:
    return parse_amount(record.get(key)) is not None


def charge_header(row: list[str]) -> bool:
    normalized = {column.strip().lower().replace(" ", "_").replace("-", "_") for column in row}
    return "description" in normalized and any(column.startswith("code|") for column in row)


def row_has_target_code(record: dict[str, Any]) -> bool:
    for found_type, found_code in _codes_from_record(record):
        normalized_type = found_type.replace("-", "").upper()
        if found_code in TARGET_CODES and normalized_type in {"CPT", "HCPCS"}:
            return True
    return False


def scan_csv_fast(path: Path) -> list[dict[str, Any]]:
    last_error = None
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            records: list[dict[str, Any]] = []
            with path.open("r", encoding=encoding, newline="") as handle:
                reader = csv.reader(handle)
                header = None
                for row in reader:
                    if charge_header(row):
                        header = row
                        break
                if header is None:
                    return []
                # Fast prefilter: parse only lines containing the target text.
                for line in handle:
                    if "93000" not in line and "93005" not in line:
                        continue
                    for values in csv.reader([line]):
                        record = {field: values[index] if index < len(values) else "" for index, field in enumerate(header)}
                        if row_has_target_code(record):
                            records.append(record)
            return records
        except UnicodeDecodeError as exc:
            last_error = exc
            continue
    if last_error:
        raise last_error
    return []


def hospital_for_source(con: sqlite3.Connection, marker: str, fallback: str) -> tuple[str, str | None]:
    rows = con.execute(
        """
        SELECT h.name, m.source_url
        FROM mrf_sources m JOIN hospitals h ON h.id = m.hospital_id
        """
    ).fetchall()
    for row in rows:
        if marker in row["source_url"]:
            return row["name"], row["source_url"]
    rows = con.execute(
        """
        SELECT h.name, p.source_url
        FROM indexed_prices p JOIN hospitals h ON h.id = p.hospital_id
        GROUP BY h.name, p.source_url
        """
    ).fetchall()
    for row in rows:
        if marker in row["source_url"]:
            return row["name"], row["source_url"]
    return fallback, None


def summarize_records(records: list[dict[str, Any]], hospital: str, source_url: str | None) -> tuple[Counter[str], list[dict[str, Any]]]:
    counts: Counter[str] = Counter()
    samples: list[dict[str, Any]] = []
    for record in records:
        counts["raw_matched_records"] += 1
        for key, label in [
            ("standard_charge|discounted_cash", "raw_has_discounted_cash"),
            ("standard_charge|gross", "raw_has_gross"),
            ("standard_charge|negotiated_dollar", "raw_has_negotiated_dollar"),
            ("standard_charge|min", "raw_has_min"),
            ("standard_charge|max", "raw_has_max"),
        ]:
            if amount_present(record, key):
                counts[label] += 1
        result = search_result_from_record(
            record,
            hospital=hospital,
            procedure_name="EKG",
            code_type="CPT",
            code="93000/93005",
            source_url=source_url,
            evidence_source="raw_price_type_audit",
        )
        if result:
            counts[f"extractor_display_{result.display_price_type}"] += 1
            counts[f"extractor_quality_{result.data_quality_flag}"] += 1
        if len(samples) < 3:
            samples.append(
                {
                    k: record.get(k)
                    for k in [
                        "description",
                        "code|1",
                        "code|1|type",
                        "code|2",
                        "code|2|type",
                        "setting",
                        "standard_charge|gross",
                        "standard_charge|discounted_cash",
                        "payer_name",
                        "plan_name",
                        "standard_charge|negotiated_dollar",
                        "standard_charge|min",
                        "standard_charge|max",
                    ]
                    if record.get(k) not in (None, "")
                }
            )
    return counts, samples


def db_summary(con: sqlite3.Connection, hospital: str) -> dict[str, Any]:
    rows = con.execute(
        """
        SELECT price_type, COALESCE(data_quality_flag, 'ok') AS quality, COUNT(*) AS c
        FROM indexed_prices p JOIN hospitals h ON h.id = p.hospital_id
        WHERE h.name = ? AND p.code_type = 'CPT' AND p.procedure_code IN ('93000', '93005')
        GROUP BY price_type, COALESCE(data_quality_flag, 'ok')
        ORDER BY price_type, quality
        """,
        (hospital,),
    ).fetchall()
    return {f"db_{row['price_type']}_{row['quality']}": row["c"] for row in rows}


def main() -> int:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    OUT.parent.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    start = time.time()
    for source in LOCAL_MRF_SOURCES:
        hospital, source_url = hospital_for_source(con, source.url_marker, source.path.stem)
        item: dict[str, Any] = {
            "hospital": hospital,
            "file": source.path.name,
            "format": source.mrf_format,
            "file_size_bytes": source.path.stat().st_size if source.path.exists() else 0,
            "source_url": source_url,
        }
        print(f"auditing {hospital} ({source.mrf_format})", flush=True)
        t0 = time.time()
        try:
            if source.mrf_format == "csv":
                records = scan_csv_fast(source.path)
            else:
                by_target = records_from_large_json_file_for_codes(
                    source.path,
                    targets=[("CPT", "93000"), ("CPT", "93005"), ("HCPCS", "93000"), ("HCPCS", "93005")],
                    max_matches_per_target=10000,
                )
                records = [record for records in by_target.values() for record in records]
            counts, samples = summarize_records(records, hospital, source_url)
            item.update(counts)
            item.update(db_summary(con, hospital))
            item["samples"] = samples
        except Exception as exc:
            item["error"] = repr(exc)
        item["elapsed_seconds"] = round(time.time() - t0, 2)
        results.append(item)
        OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"wrote={OUT}")
    print(f"elapsed_seconds={round(time.time() - start, 2)}")
    for row in results:
        print(json.dumps({k: v for k, v in row.items() if k != "samples"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
