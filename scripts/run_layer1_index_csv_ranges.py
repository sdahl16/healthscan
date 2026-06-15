from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen

from healthscan.database import connect, initialize, upsert_hospital, upsert_mrf_source
from healthscan.indexer import insert_prices, prices_from_record, record_matches


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "mrf"


@dataclass(frozen=True)
class RangeTarget:
    name: str
    domain: str
    address: str
    state: str
    zip_code: str
    cms_hpt_url: str
    source_url: str
    content_length: int
    start: int
    end: int
    output_name: str


TARGETS = (
    RangeTarget(
        name="Keck Hospital of USC",
        domain="keckmedicine.org",
        address="1500 San Pablo Street, Los Angeles, CA 90033",
        state="CA",
        zip_code="90033",
        cms_hpt_url="https://keckmedicine.org/cms-hpt.txt",
        source_url="https://hospitalpricedisclosure.com/download.aspx?pi=5fSixiuBb0ZpZwZgOthF7A*-*",
        content_length=114_762_422,
        start=90_000_000,
        end=94_999_999,
        output_name="keck-drg-470-sample.csv",
    ),
    RangeTarget(
        name="Sharp Chula Vista Medical Center",
        domain="sharp.com",
        address="751 Medical Center Court, Chula Vista, CA 91911",
        state="CA",
        zip_code="91911",
        cms_hpt_url="https://sharp.com/cms-hpt.txt",
        source_url="https://downloads.ctfassets.net/pxcfulgsd9e2/D4fRN51N03oyjM0c54C1U/cbd502f0357445b1fc46bdeaac647efc/95-2367304_sharp-chula-vista-medical-center_standardcharges.csv",
        content_length=662_916_895,
        start=5_000_000,
        end=9_999_999,
        output_name="sharp-chula-vista-drg-470-sample.csv",
    ),
)


def fetch_text(url: str, *, start: int, end: int) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 HealthScanResearch/0.1",
            "Range": f"bytes={start}-{end}",
        },
    )
    with urlopen(request, timeout=120) as response:
        return response.read().decode("utf-8-sig", errors="replace")


def header_from_head(text: str) -> str:
    for line in text.splitlines():
        if "description" in line.lower() and "code|1" in line.lower():
            return line
    raise ValueError("Could not find CMS charge header row")


def matching_lines(text: str) -> list[str]:
    return [
        line
        for line in text.splitlines()
        if "470" in line and ("MS-DRG" in line.upper() or ",DRG," in line.upper())
    ]


def build_sample(target: RangeTarget) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    head = fetch_text(target.source_url, start=0, end=200_000)
    chunk = fetch_text(target.source_url, start=target.start, end=target.end)
    header = header_from_head(head)
    rows = matching_lines(chunk)
    out_path = RAW_DIR / target.output_name
    out_path.write_text("\n".join([header, *rows]) + "\n", encoding="utf-8")
    return out_path


def index_target(connection, target: RangeTarget) -> dict[str, object]:
    sample_path = build_sample(target)
    with sample_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        matches = [row for row in reader if record_matches(row, code_type="DRG", code="470")]

    prices = []
    for row in matches:
        prices.extend(
            prices_from_record(
                row,
                procedure_name="Hip replacement",
                procedure_code="470",
                code_type="DRG",
                source_url=target.source_url,
                last_updated=row.get("last_updated_on"),
            )
        )

    hospital_id = upsert_hospital(
        connection,
        name=target.name,
        domain=target.domain,
        address=target.address,
        state=target.state,
        zip_code=target.zip_code,
        cms_hpt_url=target.cms_hpt_url,
    )
    source_id = upsert_mrf_source(
        connection,
        hospital_id=hospital_id,
        source_url=target.source_url,
        content_type="text/csv",
        content_length_bytes=target.content_length,
        mrf_format="CSV",
        status="range_sample_indexed",
    )
    inserted = insert_prices(connection, hospital_id=hospital_id, mrf_source_id=source_id, prices=prices)
    return {
        "hospital": target.name,
        "sample_path": str(sample_path),
        "drg_470_matches": len(matches),
        "indexed_price_rows": inserted,
    }


def main() -> None:
    connection = connect()
    initialize(connection)
    results = [index_target(connection, target) for target in TARGETS]
    connection.commit()
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
