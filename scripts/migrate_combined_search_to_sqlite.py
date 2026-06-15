from __future__ import annotations

import argparse
import csv
import sqlite3
from pathlib import Path
from urllib.parse import urlparse

from healthscan.database import DEFAULT_DB_PATH, connect, initialize, upsert_hospital, upsert_mrf_source


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = ROOT / "data" / "processed" / "combined_search_results.csv"
TARGET_FILES = [
    ROOT / "data" / "reference" / "layer4_hospital_targets.csv",
    ROOT / "data" / "reference" / "mvp_layer1_targets.csv",
]


def optional(value: str | None) -> str | None:
    text = (value or "").strip()
    return text or None


def amount(value: str) -> float:
    text = value.strip().replace("$", "").replace(",", "")
    if not text:
        raise ValueError("missing display_price")
    return float(text)


def load_hospital_domains() -> dict[str, str]:
    domains: dict[str, str] = {}
    for path in TARGET_FILES:
        if not path.exists():
            continue
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                name = row.get("hospital_name") or row.get("hospital_system")
                domain = row.get("domain")
                if name and domain:
                    domains[name] = domain
    return domains


def synthetic_source_url(row: dict[str, str]) -> str:
    evidence = optional(row.get("evidence_source")) or "combined_search_results"
    hospital = row["hospital"].lower().replace(" ", "-").replace("/", "-")
    procedure = row["procedure_name"].lower().replace(" ", "-").replace("/", "-")
    return f"combined://{evidence}/{hospital}/{procedure}/{row['code_type']}/{row['code']}"


def source_url_for_row(row: dict[str, str]) -> str:
    return optional(row.get("source_url")) or synthetic_source_url(row)


def domain_for_row(row: dict[str, str], domains: dict[str, str]) -> str:
    mapped = domains.get(row["hospital"])
    if mapped:
        return mapped
    parsed = urlparse(optional(row.get("source_url")) or "")
    return parsed.netloc or ""


def format_for_source(source_url: str) -> str | None:
    path = urlparse(source_url).path.lower()
    if path.endswith(".json"):
        return "json"
    if path.endswith(".csv"):
        return "csv"
    return None


def ensure_migration_columns(connection: sqlite3.Connection) -> None:
    existing = {row["name"] for row in connection.execute("PRAGMA table_info(indexed_prices)")}
    if "user_relevance_flag" not in existing:
        connection.execute("ALTER TABLE indexed_prices ADD COLUMN user_relevance_flag TEXT")
    if "user_relevance_reason" not in existing:
        connection.execute("ALTER TABLE indexed_prices ADD COLUMN user_relevance_reason TEXT")


def migrate(input_path: Path, db_path: Path = DEFAULT_DB_PATH) -> dict[str, int]:
    domains = load_hospital_domains()
    with input_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    with connect(db_path) as connection:
        initialize(connection)
        ensure_migration_columns(connection)
        connection.execute("DELETE FROM indexed_prices")

        hospital_ids: dict[str, int] = {}
        source_ids: dict[tuple[int, str], int] = {}
        inserted = 0
        for row in rows:
            hospital = row["hospital"]
            hospital_id = hospital_ids.get(hospital)
            if hospital_id is None:
                hospital_id = upsert_hospital(
                    connection,
                    name=hospital,
                    domain=domain_for_row(row, domains),
                )
                hospital_ids[hospital] = hospital_id

            source_url = source_url_for_row(row)
            source_key = (hospital_id, source_url)
            mrf_source_id = source_ids.get(source_key)
            if mrf_source_id is None:
                mrf_source_id = upsert_mrf_source(
                    connection,
                    hospital_id=hospital_id,
                    source_url=source_url,
                    mrf_format=format_for_source(source_url),
                    status="migrated_from_combined_search_results",
                )
                source_ids[source_key] = mrf_source_id

            connection.execute(
                """
                INSERT INTO indexed_prices (
                    hospital_id, mrf_source_id, procedure_name, procedure_code, code_type,
                    description, setting, price_type, amount, payer_name, plan_name,
                    allowed_amount_count, last_updated, source_url, data_quality_flag,
                    user_relevance_flag, user_relevance_reason, parse_warnings
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    hospital_id,
                    mrf_source_id,
                    row["procedure_name"],
                    row["code"],
                    row["code_type"],
                    optional(row.get("description")),
                    optional(row.get("setting")),
                    row["display_price_type"],
                    amount(row["display_price"]),
                    optional(row.get("payer_name")),
                    optional(row.get("plan_name")),
                    None,
                    None,
                    source_url,
                    optional(row.get("data_quality_flag")) or "ok",
                    optional(row.get("user_relevance_flag")) or "display_ok",
                    optional(row.get("user_relevance_reason")),
                    f"migrated_from={optional(row.get('evidence_source')) or 'combined_search_results'}",
                ),
            )
            inserted += 1

        connection.commit()

        return {
            "input_rows": len(rows),
            "inserted_rows": inserted,
            "hospitals": len(hospital_ids),
            "mrf_sources": len(source_ids),
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args()

    summary = migrate(args.input, args.db)
    for key, value in summary.items():
        print(f"{key}={value}")
    print(f"db={args.db}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
