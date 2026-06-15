from __future__ import annotations

import csv
from pathlib import Path
from urllib.request import Request, urlopen

from healthscan.indexer import record_matches


ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "data" / "raw" / "mrf" / "rady-childrens-standardcharges.csv"
OUT_PATH = ROOT / "data" / "research" / "mvp_layer2_rady_offsets.csv"
URL = "https://www.rchsd.org/wp-content/uploads/2026/03/95-1691313_rady-childrens-hospital-san-diego_standardcharges.csv"

PROCEDURES = [
    ("Colonoscopy", "CPT", "45378"),
    ("Brain MRI", "CPT", "70551"),
    ("CT abdomen and pelvis", "CPT", "74176"),
    ("Emergency department visit", "CPT", "99285"),
]


def download() -> None:
    RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    if RAW_PATH.exists() and RAW_PATH.stat().st_size > 0:
        return
    request = Request(URL, headers={"User-Agent": "Mozilla/5.0 HealthScanResearch/0.1"})
    with urlopen(request, timeout=120) as response:
        RAW_PATH.write_bytes(response.read())


def row_matches(row: dict[str, str], code_type: str, code: str) -> bool:
    return record_matches(row, code_type=code_type, code=code)


def main() -> None:
    download()
    rows: list[dict[str, str | int]] = []
    found: set[str] = set()
    with RAW_PATH.open(newline="", encoding="utf-8-sig") as handle:
        raw_reader = csv.reader(handle)
        header = None
        for raw_row in raw_reader:
            if "description" in [cell.strip() for cell in raw_row] and any(
                cell.startswith("code|") for cell in raw_row
            ):
                header = raw_row
                break
        if header is None:
            raise ValueError("Could not find Rady charge header")
        reader = csv.DictReader(handle, fieldnames=header)
        for row_number, row in enumerate(reader, start=1):
            for procedure_name, code_type, code in PROCEDURES:
                if procedure_name in found:
                    continue
                if row_matches(row, code_type, code):
                    rows.append(
                        {
                            "hospital": "Rady Children's Hospital",
                            "procedure_name": procedure_name,
                            "code_type": code_type,
                            "code": code,
                            "row_number": row_number,
                            "source_url": URL,
                            "sample_line": str({key: row.get(key, "") for key in header[:28]})[:2000],
                        }
                    )
                    found.add(procedure_name)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "hospital",
            "procedure_name",
            "code_type",
            "code",
            "row_number",
            "source_url",
            "sample_line",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"rows={len(rows)} output={OUT_PATH}")


if __name__ == "__main__":
    main()
