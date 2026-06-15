from __future__ import annotations

import json
from pathlib import Path
from urllib.request import Request, urlopen

from healthscan.database import connect, initialize, upsert_hospital, upsert_mrf_source
from healthscan.indexer import (
    address_parts,
    insert_prices,
    prices_from_standard_charge_item,
    record_matches,
)


URL = "https://www.uclahealth.org/sites/default/files/cms-hpt/956006143_ronald-reagan-ucla-medical-center_standardcharges.json"
ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "data" / "raw" / "mrf" / "ucla-ronald-reagan-standardcharges.json"


def download() -> None:
    RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    if RAW_PATH.exists() and RAW_PATH.stat().st_size > 0:
        return
    request = Request(URL, headers={"User-Agent": "Mozilla/5.0 HealthScanResearch/0.1"})
    with urlopen(request, timeout=120) as response:
        RAW_PATH.write_bytes(response.read())


def main() -> None:
    download()
    data = json.loads(RAW_PATH.read_text(encoding="utf-8-sig"))
    hospital_name = data.get("hospital_name") or "Ronald Reagan UCLA Medical Center"
    address = (data.get("hospital_address") or [None])[0]
    address, state, zip_code = address_parts(address)
    last_updated = data.get("last_updated_on") or data.get("as_of_date")

    matches = [
        item
        for item in data.get("standard_charge_information", [])
        if isinstance(item, dict) and record_matches(item, code_type="DRG", code="470")
    ]

    prices = []
    for item in matches:
        prices.extend(
            prices_from_standard_charge_item(
                item,
                procedure_name="Hip replacement",
                procedure_code="470",
                code_type="DRG",
                source_url=URL,
                last_updated=last_updated,
            )
        )

    connection = connect()
    initialize(connection)
    hospital_id = upsert_hospital(
        connection,
        name=hospital_name,
        domain="uclahealth.org",
        address=address,
        state=state,
        zip_code=zip_code,
        cms_hpt_url="https://uclahealth.org/cms-hpt.txt",
    )
    source_id = upsert_mrf_source(
        connection,
        hospital_id=hospital_id,
        source_url=URL,
        content_type="application/json",
        content_length_bytes=RAW_PATH.stat().st_size,
        mrf_format="JSON",
        mrf_date=last_updated,
        status="indexed",
    )
    inserted = insert_prices(connection, hospital_id=hospital_id, mrf_source_id=source_id, prices=prices)
    connection.commit()

    print(
        json.dumps(
            {
                "hospital": hospital_name,
                "raw_path": str(RAW_PATH),
                "drg_470_matches": len(matches),
                "indexed_price_rows": inserted,
                "db_path": str(ROOT / "data" / "processed" / "healthscan.sqlite"),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
