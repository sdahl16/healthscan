from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class IndexingTarget:
    procedure_name: str
    code_type: str
    procedure_code: str
    care_setting: str
    is_primary: bool
    priority: str
    indexing_status: str
    notes: str


def load_indexing_targets(path: Path) -> list[IndexingTarget]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [
            IndexingTarget(
                procedure_name=row["procedure_name"],
                code_type=row["code_type"],
                procedure_code=row["procedure_code"],
                care_setting=row["care_setting"],
                is_primary=row["is_primary"].lower() == "true",
                priority=row["priority"],
                indexing_status=row["indexing_status"],
                notes=row["notes"],
            )
            for row in csv.DictReader(handle)
        ]
