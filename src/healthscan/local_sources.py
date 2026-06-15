from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class LocalMrfSource:
    url_marker: str
    path: Path
    mrf_format: str
    scan_scope: str


LOCAL_MRF_SOURCES = (
    LocalMrfSource(
        url_marker="95-1691313_rady-childrens-hospital-san-diego_standardcharges.csv",
        path=ROOT / "data" / "raw" / "mrf" / "rady-childrens-standardcharges.csv",
        mrf_format="csv",
        scan_scope="full_local_csv",
    ),
    LocalMrfSource(
        url_marker="951684089_Scripps-Green-Hospital_standardcharges.csv",
        path=ROOT / "data" / "raw" / "mrf" / "scripps-green-standardcharges.csv",
        mrf_format="csv",
        scan_scope="full_local_csv",
    ),
    LocalMrfSource(
        url_marker="download.aspx?pi=5fSixiuBb0ZpZwZgOthF7A*-*",
        path=ROOT / "data" / "raw" / "mrf" / "keck-hospital-usc-standardcharges.csv",
        mrf_format="csv",
        scan_scope="full_local_csv",
    ),
    LocalMrfSource(
        url_marker="956006143_ronald-reagan-ucla-medical-center_standardcharges.json",
        path=ROOT / "data" / "raw" / "mrf" / "ucla-ronald-reagan-standardcharges.json",
        mrf_format="json",
        scan_scope="large_local_json",
    ),
    LocalMrfSource(
        url_marker="UC-San-Diego-Standard-Charges-956006144.json",
        path=ROOT / "data" / "raw" / "mrf" / "ucsd-standardcharges.json",
        mrf_format="json",
        scan_scope="large_local_json",
    ),
    LocalMrfSource(
        url_marker="95-2367304_sharp-chula-vista-medical-center_standardcharges.csv",
        path=ROOT / "data" / "raw" / "mrf" / "sharp-chula-vista-standardcharges.csv",
        mrf_format="csv",
        scan_scope="full_local_csv",
    ),
    LocalMrfSource(
        url_marker="951644600_CEDARS-SINAI-MEDICAL-CENTER_standardcharges.json",
        path=ROOT / "data" / "raw" / "mrf" / "cedars-sinai-standardcharges.json",
        mrf_format="json",
        scan_scope="large_local_json",
    ),
)


def resolve_local_source(mrf_url: str) -> LocalMrfSource | None:
    for source in LOCAL_MRF_SOURCES:
        if source.url_marker in mrf_url and source.path.exists():
            return source
    return None
