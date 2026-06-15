from __future__ import annotations

import csv
import re
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "data" / "research" / "mvp_layer2_ucsd_offsets.csv"
URL = "https://hsfiles.ucsd.edu/patientBilling/UC-San-Diego-Standard-Charges-956006144.json"
SIZE = 3_227_761_341
CHUNK_SIZE = 20_000_000

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


def fetch_range(start: int, end: int) -> str:
    request = Request(
        URL,
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
    found: dict[str, dict[str, str | int]] = {}
    patterns = {name: pattern_for(code_type, code) for name, code_type, code in PROCEDURES}
    for start in range(0, SIZE, CHUNK_SIZE):
        if len(found) == len(PROCEDURES):
            break
        end = min(SIZE - 1, start + CHUNK_SIZE - 1)
        text = fetch_range(start, end)
        for name, code_type, code in PROCEDURES:
            if name in found:
                continue
            match = patterns[name].search(text)
            if match:
                found[name] = {
                    "hospital": "UC San Diego Medical Center",
                    "procedure_name": name,
                    "code_type": code_type,
                    "code": code,
                    "range_start": start,
                    "range_end": end,
                    "match_offset": match.start(),
                    "sample_text": text[max(0, match.start() - 1000) : match.start() + 2000],
                }

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
            "sample_text",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(found.values())
    print(f"rows={len(found)} output={OUT_PATH}")


if __name__ == "__main__":
    main()
