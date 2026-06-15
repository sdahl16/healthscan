from __future__ import annotations

import csv
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from healthscan.database import DEFAULT_DB_PATH
from healthscan.translation import ProcedureTranslator


MAPPING_PATH = ROOT / "data" / "reference" / "procedure_mapping.csv"
FALLBACK_LOG_PATH = ROOT / "data" / "research" / "translation_fallback_log.csv"
OUT_PATH = ROOT / "data" / "research" / "translation_expansion_report.json"
CANDIDATES_OUT_PATH = ROOT / "data" / "research" / "translation_expansion_candidates.csv"
GAPS_OUT_PATH = ROOT / "data" / "research" / "translation_indexing_gaps.csv"
SUPPORTED_CODE_TYPES = {"CPT", "DRG", "HCPCS"}


def indexed_code_counts(db_path: Path = DEFAULT_DB_PATH) -> dict[tuple[str, str], int]:
    if not db_path.exists():
        return {}
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT UPPER(code_type) AS code_type, procedure_code, COUNT(DISTINCT hospital_id) AS hospitals
            FROM indexed_prices
            GROUP BY UPPER(code_type), procedure_code
            """
        ).fetchall()
    return {(row[0], row[1]): int(row[2]) for row in rows}


def mapping_coverage() -> list[dict[str, object]]:
    counts = indexed_code_counts()
    translator = ProcedureTranslator(mapping_path=MAPPING_PATH)
    rows: list[dict[str, object]] = []
    for mapping in translator.mappings:
        codes = mapping.codes
        indexed = [
            {
                "code_type": code.code_type,
                "procedure_code": code.procedure_code,
                "indexed_hospitals": counts.get((code.code_type, code.procedure_code), 0),
                "is_primary": code.is_primary,
            }
            for code in codes
        ]
        primary = indexed[0] if indexed else {"indexed_hospitals": 0}
        rows.append(
            {
                "plain_name": mapping.description,
                "primary_code_type": mapping.primary_code_type,
                "primary_code": mapping.primary_code,
                "setting": mapping.setting,
                "primary_indexed_hospitals": primary["indexed_hospitals"],
                "any_indexed_hospitals": max((int(item["indexed_hospitals"]) for item in indexed), default=0),
                "codes": indexed,
            }
        )
    return rows


def fallback_expansion_candidates() -> list[dict[str, object]]:
    if not FALLBACK_LOG_PATH.exists():
        return []
    counts = Counter()
    raw_by_query: dict[str, str] = {}
    with FALLBACK_LOG_PATH.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("status") != "match":
                continue
            query = (row.get("query") or "").strip().lower()
            if not query:
                continue
            counts[query] += 1
            raw_by_query.setdefault(query, row.get("raw_output") or "")
    candidates = []
    for query, count in counts.most_common(25):
        candidates.append(
            {
                "query": query,
                "fallback_hits": count,
                "sample_output": _safe_json_preview(raw_by_query.get(query, "")),
            }
        )
    return candidates


def mapped_code_keys() -> set[tuple[str, str]]:
    translator = ProcedureTranslator(mapping_path=MAPPING_PATH)
    return {
        (code.code_type, code.procedure_code)
        for mapping in translator.mappings
        for code in mapping.codes
    }


def build_candidate_rows() -> list[dict[str, object]]:
    if not FALLBACK_LOG_PATH.exists():
        return []
    counts = indexed_code_counts()
    mapped = mapped_code_keys()
    rows: list[dict[str, object]] = []
    seen: set[tuple[str, str, str]] = set()
    with FALLBACK_LOG_PATH.open(newline="", encoding="utf-8") as handle:
        for log_row in csv.DictReader(handle):
            if log_row.get("status") != "match":
                continue
            query = (log_row.get("query") or "").strip().lower()
            for candidate in _safe_json_preview(log_row.get("raw_output") or ""):
                code_type = str(candidate.get("code_type") or "").upper()
                procedure_code = str(candidate.get("procedure_code") or "").strip()
                plain_name = str(candidate.get("plain_name") or "").strip()
                if code_type not in SUPPORTED_CODE_TYPES or not procedure_code or not plain_name:
                    continue
                key = (query, code_type, procedure_code)
                if key in seen:
                    continue
                seen.add(key)
                indexed_hospitals = counts.get((code_type, procedure_code), 0)
                is_mapped = (code_type, procedure_code) in mapped
                if is_mapped:
                    recommendation = "already_mapped"
                elif indexed_hospitals > 0 and code_type == "CPT":
                    recommendation = "add_to_lookup"
                elif indexed_hospitals > 0:
                    recommendation = "review_for_lookup"
                else:
                    recommendation = "cms_gap"
                rows.append(
                    {
                        "query": query,
                        "plain_name": plain_name,
                        "primary_code_type": code_type,
                        "primary_code": procedure_code,
                        "setting": candidate.get("setting") or "",
                        "indexed_hospitals": indexed_hospitals,
                        "recommendation": recommendation,
                    }
                )
    rows.sort(
        key=lambda row: (
            {"add_to_lookup": 0, "review_for_lookup": 1, "cms_gap": 2, "already_mapped": 3}.get(
                str(row["recommendation"]),
                9,
            ),
            str(row["primary_code_type"]) != "CPT",
            str(row["plain_name"]),
        )
    )
    return rows


def write_candidate_csv(rows: list[dict[str, object]], path: Path = CANDIDATES_OUT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "query",
        "plain_name",
        "primary_code_type",
        "primary_code",
        "setting",
        "indexed_hospitals",
        "recommendation",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_gap_rows(coverage: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in coverage:
        primary_indexed = int(item["primary_indexed_hospitals"])
        any_indexed = int(item["any_indexed_hospitals"])
        if primary_indexed > 0:
            continue
        priority = "primary_code_gap"
        if any_indexed > 0:
            priority = "primary_gap_alternate_available"
        if item["primary_code_type"] == "DRG":
            priority = f"{priority}_drg"
        rows.append(
            {
                "plain_name": item["plain_name"],
                "primary_code_type": item["primary_code_type"],
                "primary_code": item["primary_code"],
                "setting": item["setting"],
                "primary_indexed_hospitals": primary_indexed,
                "any_indexed_hospitals": any_indexed,
                "priority": priority,
            }
        )
    rows.sort(
        key=lambda row: (
            str(row["primary_code_type"]) != "CPT",
            -int(row["any_indexed_hospitals"]),
            str(row["plain_name"]),
        )
    )
    return rows


def primary_swap_candidates(coverage: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in coverage:
        if int(item["primary_indexed_hospitals"]) > 0 or int(item["any_indexed_hospitals"]) == 0:
            continue
        alternates = [
            code
            for code in item["codes"]  # type: ignore[index]
            if not code["is_primary"] and int(code["indexed_hospitals"]) > 0
        ]
        if not alternates:
            continue
        best = sorted(alternates, key=lambda code: int(code["indexed_hospitals"]), reverse=True)[0]
        rows.append(
            {
                "plain_name": item["plain_name"],
                "current_primary": f"{item['primary_code_type']}:{item['primary_code']}",
                "suggested_primary": f"{best['code_type']}:{best['procedure_code']}",
                "suggested_indexed_hospitals": best["indexed_hospitals"],
                "reason": "alternate_code_has_indexed_coverage",
            }
        )
    return rows


def write_gap_csv(rows: list[dict[str, object]], path: Path = GAPS_OUT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "plain_name",
        "primary_code_type",
        "primary_code",
        "setting",
        "primary_indexed_hospitals",
        "any_indexed_hospitals",
        "priority",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _safe_json_preview(raw_output: str) -> list[dict[str, object]]:
    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    preview = []
    for item in parsed[:3]:
        if not isinstance(item, dict):
            continue
        preview.append(
            {
                "plain_name": item.get("plain_name"),
                "procedure_code": item.get("procedure_code"),
                "code_type": item.get("code_type"),
                "setting": item.get("setting"),
            }
        )
    return preview


def main() -> int:
    coverage = mapping_coverage()
    candidate_rows = build_candidate_rows()
    gap_rows = build_gap_rows(coverage)
    swap_rows = primary_swap_candidates(coverage)
    report = {
        "summary": {
            "mapped_procedures": len(coverage),
            "primary_codes_with_indexed_rows": sum(1 for row in coverage if int(row["primary_indexed_hospitals"]) > 0),
            "procedures_with_any_indexed_rows": sum(1 for row in coverage if int(row["any_indexed_hospitals"]) > 0),
            "cpt_primary_rows": sum(1 for row in coverage if row["primary_code_type"] == "CPT"),
            "drg_primary_rows": sum(1 for row in coverage if row["primary_code_type"] == "DRG"),
            "hcpcs_primary_rows": sum(1 for row in coverage if row["primary_code_type"] == "HCPCS"),
            "expansion_candidate_rows": len(candidate_rows),
            "add_to_lookup_candidates": sum(1 for row in candidate_rows if row["recommendation"] == "add_to_lookup"),
            "cms_gap_candidates": sum(1 for row in candidate_rows if row["recommendation"] == "cms_gap"),
            "mapping_primary_code_gaps": len(gap_rows),
            "primary_swap_candidates": len(swap_rows),
        },
        "mapping_coverage": coverage,
        "primary_swap_candidates": swap_rows,
        "fallback_expansion_candidates": fallback_expansion_candidates(),
        "recommended_next_steps": [
            "Add high-frequency fallback matches as CPT rows first when indexed coverage exists.",
            "Keep DRG additions gated on indexed_prices coverage.",
            "Keep APC disabled until indexed_prices contains APC rows.",
        ],
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_candidate_csv(candidate_rows)
    write_gap_csv(gap_rows)
    print(f"output={OUT_PATH}")
    print(f"candidate_csv={CANDIDATES_OUT_PATH}")
    print(f"gap_csv={GAPS_OUT_PATH}")
    print(json.dumps(report["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
