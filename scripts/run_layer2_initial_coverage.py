from __future__ import annotations

import csv
import json
from pathlib import Path

from healthscan.indexer import csv_matching_records, json_matching_records


ROOT = Path(__file__).resolve().parents[1]
PROCEDURES_PATH = ROOT / "data" / "reference" / "procedure_mapping.csv"
OUT_PATH = ROOT / "data" / "research" / "mvp_layer2_initial_coverage.csv"


SOURCES = (
    {
        "hospital": "Ronald Reagan UCLA Medical Center",
        "city": "Los Angeles, CA",
        "path": ROOT / "data" / "raw" / "mrf" / "ucla-ronald-reagan-standardcharges.json",
        "kind": "json_full",
    },
    {
        "hospital": "Scripps Green Hospital",
        "city": "San Diego, CA",
        "path": ROOT / "data" / "raw" / "mrf" / "scripps-green-standardcharges-sample.csv",
        "kind": "csv_sample",
    },
    {
        "hospital": "Keck Hospital of USC",
        "city": "Los Angeles, CA",
        "path": ROOT / "data" / "raw" / "mrf" / "keck-drg-470-sample.csv",
        "kind": "csv_drg470_sample",
    },
    {
        "hospital": "Sharp Chula Vista Medical Center",
        "city": "San Diego, CA",
        "path": ROOT / "data" / "raw" / "mrf" / "sharp-chula-vista-drg-470-sample.csv",
        "kind": "csv_drg470_sample",
    },
    {
        "hospital": "UC San Diego Medical Center",
        "city": "San Diego, CA",
        "path": ROOT / "data" / "raw" / "mrf" / "ucsd-drg-470-sample.json",
        "kind": "json_drg470_sample",
    },
)


def load_procedures() -> list[dict[str, str]]:
    with PROCEDURES_PATH.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def count_matches(path: Path, kind: str, code_type: str, code: str) -> int | None:
    if not path.exists():
        return None
    if kind.startswith("json"):
        return len(json_matching_records(path, code_type=code_type, code=code))
    return len(csv_matching_records(path, code_type=code_type, code=code))


def main() -> None:
    rows: list[dict[str, object]] = []
    for procedure in load_procedures():
        for source in SOURCES:
            match_count = count_matches(
                source["path"],
                str(source["kind"]),
                procedure["primary_code_type"],
                procedure["primary_code"],
            )
            rows.append(
                {
                    "procedure_name": procedure["plain_language_name"],
                    "code_type": procedure["primary_code_type"],
                    "code": procedure["primary_code"],
                    "hospital": source["hospital"],
                    "city": source["city"],
                    "source_kind": source["kind"],
                    "source_path": source["path"],
                    "match_count": "" if match_count is None else match_count,
                    "coverage_result": "missing_source"
                    if match_count is None
                    else ("present" if match_count > 0 else "not_found"),
                }
            )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    summary: dict[str, set[str]] = {}
    for row in rows:
        if row["coverage_result"] == "present":
            summary.setdefault(str(row["procedure_name"]), set()).add(str(row["hospital"]))

    print(json.dumps({name: len(hospitals) for name, hospitals in summary.items()}, indent=2))
    print(OUT_PATH)


if __name__ == "__main__":
    main()
