from __future__ import annotations

import csv
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "data" / "research" / "mvp_layer2_csv_offsets.csv"
CHUNK_SIZE = 10_000_000

TARGETS = [
    {
        "hospital": "Keck Hospital of USC",
        "url": "https://hospitalpricedisclosure.com/download.aspx?pi=5fSixiuBb0ZpZwZgOthF7A*-*",
        "size": 114_762_422,
    },
    {
        "hospital": "Scripps Green Hospital",
        "url": "https://apps.scripps.org/pricetransparency/951684089_Scripps-Green-Hospital_standardcharges.csv",
        "size": 537_741_430,
    },
    {
        "hospital": "Sharp Chula Vista Medical Center",
        "url": "https://downloads.ctfassets.net/pxcfulgsd9e2/D4fRN51N03oyjM0c54C1U/cbd502f0357445b1fc46bdeaac647efc/95-2367304_sharp-chula-vista-medical-center_standardcharges.csv",
        "size": 662_916_895,
    },
]

PROCEDURES = [
    ("Colonoscopy", "CPT", "45378"),
    ("Vaginal delivery", "DRG", "807"),
    ("C-section", "DRG", "783"),
    ("Appendectomy", "DRG", "341"),
    ("Cardiac catheterization", "DRG", "287"),
    ("Brain MRI", "CPT", "70551"),
    ("CT abdomen and pelvis", "CPT", "74176"),
    ("Emergency department visit", "CPT", "99285"),
]


def fetch_range(url: str, start: int, end: int) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 HealthScanResearch/0.1",
            "Range": f"bytes={start}-{end}",
        },
    )
    with urlopen(request, timeout=120) as response:
        return response.read().decode("utf-8-sig", errors="replace")


def parse_line(line: str) -> list[str]:
    try:
        return next(csv.reader([line]))
    except csv.Error:
        return []


def row_matches(line: str, code_type: str, code: str) -> bool:
    cells = [cell.strip().upper() for cell in parse_line(line)[:12]]
    wanted_type = code_type.upper()
    wanted_code = code.upper()
    for index in range(len(cells) - 1):
        found_code = cells[index]
        found_type = cells[index + 1].replace("-", "")
        if found_code != wanted_code:
            continue
        if found_type == wanted_type or (wanted_type == "DRG" and found_type == "MSDRG"):
            return True
    return False


def main() -> None:
    rows: list[dict[str, str | int]] = []
    for target in TARGETS:
        found = {name: False for name, _, _ in PROCEDURES}
        for start in range(0, target["size"], CHUNK_SIZE):
            if all(found.values()):
                break
            end = min(target["size"] - 1, start + CHUNK_SIZE - 1)
            text = fetch_range(str(target["url"]), start, end)
            lines = text.splitlines()
            for procedure_name, code_type, code in PROCEDURES:
                if found[procedure_name]:
                    continue
                for line in lines:
                    if row_matches(line, code_type, code):
                        rows.append(
                            {
                                "hospital": target["hospital"],
                                "procedure_name": procedure_name,
                                "code_type": code_type,
                                "code": code,
                                "range_start": start,
                                "range_end": end,
                                "sample_line": line[:2000],
                            }
                        )
                        found[procedure_name] = True
                        break

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "hospital",
                "procedure_name",
                "code_type",
                "code",
                "range_start",
                "range_end",
                "sample_line",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"rows={len(rows)} output={OUT_PATH}")


if __name__ == "__main__":
    main()
