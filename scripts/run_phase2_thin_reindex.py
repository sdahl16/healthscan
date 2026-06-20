from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PHASE_DIR = ROOT / "data" / "processed" / "phase2_thin_reindex"
COMBINED_OUTPUT = ROOT / "data" / "processed" / "layer4_local_search_results.csv"
COMBINED_AUDIT = ROOT / "data" / "research" / "phase2_thin_reindex_audit.csv"

FILES = [
    "cedars-sinai-standardcharges.json",
    "community-memorial-ventura-standardcharges.csv",
    "hoag-newport-beach-standardcharges.csv",
    "hollywood-presbyterian-standardcharges.json",
    "huntington-hospital-standardcharges.csv",
    "keck-hospital-usc-standardcharges.csv",
    "loma-linda-university-medical-center-standardcharges.csv",
    "los-robles-regional-medical-center-standardcharges.json",
    "memorialcare-orange-coast-standardcharges.json",
    "paradise-valley-standardcharges.json",
    "rady-childrens-standardcharges.csv",
    "riverside-community-hospital-standardcharges.json",
    "scripps-green-standardcharges.csv",
    "scripps-memorial-la-jolla-standardcharges.csv",
    "scripps-mercy-san-diego-standardcharges.csv",
    "sharp-chula-vista-standardcharges.csv",
    "sharp-grossmont-standardcharges.csv",
    "sharp-memorial-standardcharges.csv",
    "tri-city-medical-center-standardcharges.csv",
    "uci-medical-center-standardcharges.json",
    "ucla-ronald-reagan-standardcharges.json",
    "ucsd-standardcharges.json",
]


def run_file(file_name: str) -> None:
    output = PHASE_DIR / f"{Path(file_name).stem}.csv"
    audit = PHASE_DIR / f"{Path(file_name).stem}.audit.csv"
    cmd = [
        sys.executable,
        "scripts/run_layer4_fast_price_type_reindex.py",
        "--include-alternates",
        "--only-file",
        file_name,
        "--output",
        str(output),
        "--audit-output",
        str(audit),
    ]
    print(f"phase_start={file_name}", flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True, timeout=240)
    print(f"phase_done={file_name}", flush=True)


def combine_csvs(paths: list[Path], output: Path) -> int:
    fieldnames: list[str] = []
    rows: list[dict[str, str]] = []
    for path in paths:
        if not path.exists() or path.stat().st_size == 0:
            continue
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for fieldname in reader.fieldnames or []:
                if fieldname not in fieldnames:
                    fieldnames.append(fieldname)
            rows.extend(reader)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def main() -> int:
    PHASE_DIR.mkdir(parents=True, exist_ok=True)
    for file_name in FILES:
        run_file(file_name)

    result_rows = combine_csvs([PHASE_DIR / f"{Path(name).stem}.csv" for name in FILES], COMBINED_OUTPUT)
    audit_rows = combine_csvs([PHASE_DIR / f"{Path(name).stem}.audit.csv" for name in FILES], COMBINED_AUDIT)
    print(f"combined_layer4_rows={result_rows}")
    print(f"combined_audit_rows={audit_rows}")
    print(f"output={COMBINED_OUTPUT}")
    print(f"audit={COMBINED_AUDIT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
