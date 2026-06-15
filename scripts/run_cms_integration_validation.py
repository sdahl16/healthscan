from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from healthscan.cms_query import search_indexed_prices
from healthscan.database import DEFAULT_DB_PATH
from healthscan.translation import ProcedureTranslator


CASES = (
    ("colonoscopy", "CPT", "45378"),
    ("hip replacement", "DRG", "470"),
    ("vaginal delivery", "DRG", "807"),
    ("appendectomy", "CPT", "44970"),
    ("screening colonoscopy", "HCPCS", "G0121"),
)


def indexed_count(connection: sqlite3.Connection, code_type: str, procedure_code: str) -> int:
    row = connection.execute(
        """
        SELECT COUNT(*)
        FROM indexed_prices
        WHERE UPPER(code_type) = ? AND procedure_code = ?
        """,
        (code_type, procedure_code),
    ).fetchone()
    return int(row[0])


def main() -> int:
    if not DEFAULT_DB_PATH.exists():
        print(f"missing_db={DEFAULT_DB_PATH}")
        return 2

    translator = ProcedureTranslator()
    failures = 0
    with sqlite3.connect(DEFAULT_DB_PATH) as connection:
        for query, expected_type, expected_code in CASES:
            translation = translator.translate(query)
            translated_codes = [
                (code.code_type, code.procedure_code)
                for candidate in translation.candidates
                for code in candidate.codes
            ]
            expected_present = (expected_type, expected_code) in translated_codes
            count = indexed_count(connection, expected_type, expected_code)
            search_status, hits = search_indexed_prices(query)
            passed = translation.status == "match" and expected_present and count > 0 and search_status == "ok"
            failures += int(not passed)
            print(
                " ".join(
                    (
                        f"query={query!r}",
                        f"expected={expected_type}:{expected_code}",
                        f"translated={expected_present}",
                        f"indexed_rows={count}",
                        f"search_status={search_status}",
                        f"deduped_hospitals={len(hits)}",
                        f"passed={str(passed).lower()}",
                    )
                )
            )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
