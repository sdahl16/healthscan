import csv
from pathlib import Path

from healthscan.indexing_worklist import load_indexing_targets


def test_load_indexing_targets_parses_bool() -> None:
    path = Path("data") / "tmp" / "tests" / "worklist.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "procedure_name",
                "code_type",
                "procedure_code",
                "care_setting",
                "is_primary",
                "priority",
                "indexing_status",
                "notes",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "procedure_name": "Gallbladder removal",
                "code_type": "CPT",
                "procedure_code": "47562",
                "care_setting": "outpatient",
                "is_primary": "true",
                "priority": "1",
                "indexing_status": "needs_socal_indexing",
                "notes": "test",
            }
        )

    targets = load_indexing_targets(path)

    assert targets[0].procedure_name == "Gallbladder removal"
    assert targets[0].is_primary is True
    assert targets[0].procedure_code == "47562"
