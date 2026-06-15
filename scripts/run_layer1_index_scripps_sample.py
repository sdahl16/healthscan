from __future__ import annotations

import json
from pathlib import Path
from urllib.request import Request, urlopen

from healthscan.database import connect, initialize, upsert_hospital, upsert_mrf_source
from healthscan.indexer import csv_matching_records, insert_prices, prices_from_record


URL = "https://apps.scripps.org/pricetransparency/951684089_Scripps-Green-Hospital_standardcharges.csv"
ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "data" / "raw" / "mrf" / "scripps-green-standardcharges-sample.csv"
SAMPLE_BYTES = 5_000_000


def download_sample() -> None:
    RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    request = Request(
        URL,
        headers={
            "User-Agent": "Mozilla/5.0 HealthScanResearch/0.1",
            "Range": f"bytes=0-{SAMPLE_BYTES - 1}",
        },
    )
    with urlopen(request, timeout=120) as response:
        RAW_PATH.write_bytes(response.read())


def main() -> None:
    download_sample()
    matches = csv_matching_records(RAW_PATH, code_type="DRG", code="470")
    prices = []
    for row in matches:
        prices.extend(
            prices_from_record(
                row,
                procedure_name="Hip replacement",
                procedure_code="470",
                code_type="DRG",
                source_url=URL,
                last_updated=row.get("last_updated_on"),
            )
        )

    connection = connect()
    initialize(connection)
    hospital_id = upsert_hospital(
        connection,
        name="Scripps Green Hospital",
        domain="scripps.org",
        address="10666 North Torrey Pines Road, La Jolla, CA 92037",
        state="CA",
        zip_code="92037",
        cms_hpt_url="https://scripps.org/cms-hpt.txt",
    )
    source_id = upsert_mrf_source(
        connection,
        hospital_id=hospital_id,
        source_url=URL,
        content_type="text/csv",
        content_length_bytes=537_741_430,
        mrf_format="CSV",
        status="sample_indexed",
    )
    inserted = insert_prices(connection, hospital_id=hospital_id, mrf_source_id=source_id, prices=prices)
    connection.commit()
    print(
        json.dumps(
            {
                "hospital": "Scripps Green Hospital",
                "raw_path": str(RAW_PATH),
                "sample_bytes": RAW_PATH.stat().st_size,
                "drg_470_matches": len(matches),
                "indexed_price_rows": inserted,
                "db_path": str(ROOT / "data" / "processed" / "healthscan.sqlite"),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
