from __future__ import annotations

import csv
from pathlib import Path

from healthscan.translation import ProcedureTranslator


ROOT = Path(__file__).resolve().parents[1]
FUNCTIONALITY_RESULTS_PATH = ROOT / "data" / "research" / "socal_functionality_results.csv"
OUT_PATH = ROOT / "data" / "research" / "indexing_expansion_worklist.csv"


def main() -> int:
    translator = ProcedureTranslator()
    rows: list[dict[str, str]] = []
    with FUNCTIONALITY_RESULTS_PATH.open(newline="", encoding="utf-8") as handle:
        for result in csv.DictReader(handle):
            if result["status"] != "no_results":
                continue
            translation = translator.translate(result["query"])
            if translation.status != "match":
                rows.append(
                    {
                        "procedure_name": result["query"],
                        "code_type": "",
                        "procedure_code": "",
                        "care_setting": "",
                        "is_primary": "",
                        "priority": "blocked",
                        "indexing_status": f"translation_{translation.status}",
                        "notes": translation.message or translation.clarifying_question or "",
                    }
                )
                continue
            for code in translation.candidates[0].codes:
                rows.append(
                    {
                        "procedure_name": translation.candidates[0].plain_label,
                        "code_type": code.code_type,
                        "procedure_code": code.procedure_code,
                        "care_setting": code.care_setting,
                        "is_primary": str(code.is_primary).lower(),
                        "priority": "1" if code.is_primary else "2",
                        "indexing_status": "needs_socal_indexing",
                        "notes": "Generated from South California functionality no-results row.",
                    }
                )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "procedure_name",
            "code_type",
            "procedure_code",
            "care_setting",
            "is_primary",
            "priority",
            "indexing_status",
            "notes",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    primary_count = sum(1 for row in rows if row["is_primary"] == "true")
    print(f"procedures_needing_indexing={len({row['procedure_name'] for row in rows})}")
    print(f"code_targets={len(rows)}")
    print(f"primary_code_targets={primary_count}")
    print(f"worklist={OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
