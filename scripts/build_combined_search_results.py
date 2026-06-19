from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUTS = [
    ROOT / "data" / "processed" / "layer3_search_results.csv",
    ROOT / "data" / "processed" / "layer4_local_search_results.csv",
]
OUT_PATH = ROOT / "data" / "processed" / "combined_search_results.csv"


def main() -> int:
    rows: list[dict[str, str]] = []
    seen: set[tuple[str, ...]] = set()
    fieldnames: list[str] = []
    for path in INPUTS:
        if not path.exists():
            continue
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for fieldname in reader.fieldnames or []:
                if fieldname not in fieldnames:
                    fieldnames.append(fieldname)
            for row in reader:
                key = (
                    row["hospital"],
                    row["procedure_name"],
                    row["code_type"],
                    row["code"],
                    row["description"],
                    row["display_price_type"],
                    row["display_price"],
                    row["payer_name"],
                    row["plan_name"],
                )
                if key in seen:
                    continue
                seen.add(key)
                rows.append(row)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"combined_rows={len(rows)}")
    print(f"output={OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
