from __future__ import annotations

import csv
from pathlib import Path

from healthscan.indexing_worklist import load_indexing_targets


ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "data" / "research" / "layer4_scan_engine_audit.csv"
WORKLIST_PATH = ROOT / "data" / "research" / "indexing_expansion_worklist.csv"
OUT_PATH = ROOT / "data" / "research" / "layer4_scan_matrix.csv"


def main() -> int:
    targets = load_indexing_targets(WORKLIST_PATH)
    rows: list[dict[str, str]] = []
    with AUDIT_PATH.open(newline="", encoding="utf-8") as handle:
        for hospital in csv.DictReader(handle):
            if hospital["engine_status"] not in {"search_ready", "source_known_needs_indexing"}:
                continue
            if not hospital["mrf_url"]:
                continue
            for target in targets:
                rows.append(
                    {
                        "hospital_name": hospital["hospital_name"],
                        "hospital_system": hospital["hospital_system"],
                        "region": hospital["region"],
                        "mrf_url": hospital["mrf_url"],
                        "hospital_engine_status": hospital["engine_status"],
                        "procedure_name": target.procedure_name,
                        "code_type": target.code_type,
                        "procedure_code": target.procedure_code,
                        "care_setting": target.care_setting,
                        "is_primary": str(target.is_primary).lower(),
                        "scan_priority": target.priority,
                        "scan_status": "queued",
                    }
                )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
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
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"scan_jobs={len(rows)}")
    print(f"hospitals={len({row['hospital_name'] for row in rows})}")
    print(f"code_targets={len({(row['procedure_name'], row['code_type'], row['procedure_code']) for row in rows})}")
    print(f"matrix={OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
