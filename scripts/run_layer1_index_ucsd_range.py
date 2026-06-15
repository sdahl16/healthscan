from __future__ import annotations

import json
from pathlib import Path
from urllib.request import Request, urlopen

from healthscan.database import connect, initialize, upsert_hospital, upsert_mrf_source
from healthscan.indexer import insert_prices, prices_from_standard_charge_item, record_matches


URL = "https://hsfiles.ucsd.edu/patientBilling/UC-San-Diego-Standard-Charges-956006144.json"
ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "data" / "raw" / "mrf" / "ucsd-drg-470-sample.json"
CONTENT_LENGTH = 3_227_761_341
START = 145_500_000
END = 148_500_000


def fetch_range() -> str:
    request = Request(
        URL,
        headers={
            "User-Agent": "Mozilla/5.0 HealthScanResearch/0.1",
            "Range": f"bytes={START}-{END}",
        },
    )
    with urlopen(request, timeout=120) as response:
        return response.read().decode("utf-8", errors="replace")


def extract_json_object(text: str) -> dict:
    marker = '"description":"Major Hip And Knee Joint Replacement Or Reattachment Of Lower Extremity Without McC"'
    marker_index = text.find(marker)
    if marker_index < 0:
        raise ValueError("Could not find UCSD DRG 470 marker in range sample")

    start = text.rfind("{", 0, marker_index)
    if start < 0:
        raise ValueError("Could not find object start")

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : index + 1])
    raise ValueError("Could not find object end")


def main() -> None:
    RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    chunk = fetch_range()
    item = extract_json_object(chunk)
    RAW_PATH.write_text(json.dumps(item, indent=2), encoding="utf-8")

    if not record_matches(item, code_type="DRG", code="470"):
        raise ValueError("Extracted UCSD object does not match DRG 470")

    prices = prices_from_standard_charge_item(
        item,
        procedure_name="Hip replacement",
        procedure_code="470",
        code_type="DRG",
        source_url=URL,
        last_updated="2026-04-01",
    )

    connection = connect()
    initialize(connection)
    hospital_id = upsert_hospital(
        connection,
        name="UC San Diego Medical Center",
        domain="health.ucsd.edu",
        address="200 West Arbor Dr, San Diego, CA 92103",
        state="CA",
        zip_code="92103",
        cms_hpt_url="https://health.ucsd.edu/cms-hpt.txt",
    )
    source_id = upsert_mrf_source(
        connection,
        hospital_id=hospital_id,
        source_url=URL,
        content_type="application/json",
        content_length_bytes=CONTENT_LENGTH,
        mrf_format="JSON",
        mrf_date="2026-04-01",
        status="range_sample_indexed",
    )
    inserted = insert_prices(connection, hospital_id=hospital_id, mrf_source_id=source_id, prices=prices)
    connection.commit()

    print(
        json.dumps(
            {
                "hospital": "UC San Diego Medical Center",
                "raw_path": str(RAW_PATH),
                "indexed_price_rows": inserted,
                "min_amount": min((price.amount for price in prices), default=None),
                "max_amount": max((price.amount for price in prices), default=None),
                "db_path": str(ROOT / "data" / "processed" / "healthscan.sqlite"),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
