from __future__ import annotations

import csv
import re
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "data" / "research" / "mvp_layer2_providence_offsets.csv"
CHUNK_SIZE = 10_000_000

TARGETS = [
    (
        "Providence Cedars-Sinai Tarzana Medical Center",
        "https://pricetransparency.providence.org/socal/live/833972614_providence-cedars-sinai-tarzana-medical-center_standardcharges.json",
        198_679_443,
    ),
    (
        "Providence Holy Cross Medical Center",
        "https://pricetransparency.providence.org/socal/live/954582647_providence-holy-cross-medical-center_standardcharges.json",
        224_921_136,
    ),
    (
        "Providence Saint Joseph Medical Center",
        "https://pricetransparency.providence.org/socal/live/951675600_providence-st-joseph-medical-center_standardcharges.json",
        225_700_767,
    ),
]

PROCEDURES = [
    ("Colonoscopy", "CPT", "45378"),
    ("Appendectomy", "DRG", "341"),
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
        return response.read().decode("utf-8", errors="replace")


def pattern_for(code_type: str, code: str) -> re.Pattern[str]:
    if code_type.upper() == "DRG":
        type_pattern = r'(?:MS-DRG|MSDRG|DRG|TRIS-DRG)'
    else:
        type_pattern = re.escape(code_type.upper())
    return re.compile(
        rf'("code"\s*:\s*"{re.escape(code)}"[^{{}}]{{0,300}}"type"\s*:\s*"{type_pattern}"|'
        rf'"type"\s*:\s*"{type_pattern}"[^{{}}]{{0,300}}"code"\s*:\s*"{re.escape(code)}")',
        re.IGNORECASE,
    )


def main() -> None:
    rows: list[dict[str, str | int]] = []
    patterns = {name: pattern_for(code_type, code) for name, code_type, code in PROCEDURES}
    for hospital, url, size in TARGETS:
        found: set[str] = set()
        for start in range(0, size, CHUNK_SIZE):
            if len(found) == len(PROCEDURES):
                break
            end = min(size - 1, start + CHUNK_SIZE - 1)
            text = fetch_range(url, start, end)
            for name, code_type, code in PROCEDURES:
                if name in found:
                    continue
                match = patterns[name].search(text)
                if not match:
                    continue
                rows.append(
                    {
                        "hospital": hospital,
                        "procedure_name": name,
                        "code_type": code_type,
                        "code": code,
                        "range_start": start,
                        "range_end": end,
                        "match_offset": match.start(),
                        "source_url": url,
                        "sample_text": text[max(0, match.start() - 1000) : match.start() + 2000],
                    }
                )
                found.add(name)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "hospital",
            "procedure_name",
            "code_type",
            "code",
            "range_start",
            "range_end",
            "match_offset",
            "source_url",
            "sample_text",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"rows={len(rows)} output={OUT_PATH}")


if __name__ == "__main__":
    main()
