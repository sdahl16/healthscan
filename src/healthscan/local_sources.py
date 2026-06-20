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
    LocalMrfSource(
        url_marker='300284087_HOLLYWOOD-PRESBYTERIAN-MEDICAL-CENTER_STANDARDCHARGES.json',
        path=ROOT / "data" / "raw" / "mrf" / 'hollywood-presbyterian-standardcharges.json',
        mrf_format='json',
        scan_scope='large_local_json',
    ),
    LocalMrfSource(
        url_marker='951644036_HUNTINGTON-HOSPITAL_standardcharges.csv',
        path=ROOT / "data" / "raw" / "mrf" / 'huntington-hospital-standardcharges.csv',
        mrf_format='csv',
        scan_scope='full_local_csv',
    ),
    LocalMrfSource(
        url_marker='952226406_regents-of-the-university-of-california-at-irvine-hospital_standardcharges.json',
        path=ROOT / "data" / "raw" / "mrf" / 'uci-medical-center-standardcharges.json',
        mrf_format='json',
        scan_scope='large_local_json',
    ),
    LocalMrfSource(
        url_marker='951643327_hoag-memorial-hospital-presbyterian_standardcharges.csv',
        path=ROOT / "data" / "raw" / "mrf" / 'hoag-newport-beach-standardcharges.csv',
        mrf_format='csv',
        scan_scope='full_local_csv',
    ),
    LocalMrfSource(
        url_marker='330687414_memorialcare-orange-coast-medical-center_standardcharges.json',
        path=ROOT / "data" / "raw" / "mrf" / 'memorialcare-orange-coast-standardcharges.json',
        mrf_format='json',
        scan_scope='large_local_json',
    ),
    LocalMrfSource(
        url_marker='llu-mc/charges/export',
        path=ROOT / "data" / "raw" / "mrf" / 'loma-linda-university-medical-center-standardcharges.csv',
        mrf_format='csv',
        scan_scope='full_local_csv',
    ),
    LocalMrfSource(
        url_marker='33-0751869_RIVERSIDE-COMMUNITY-HOSPITAL_standardcharges.json',
        path=ROOT / "data" / "raw" / "mrf" / 'riverside-community-hospital-standardcharges.json',
        mrf_format='json',
        scan_scope='large_local_json',
    ),
    LocalMrfSource(
        url_marker='952126937_Tri-City-Medical-Center_standardcharges.csv',
        path=ROOT / "data" / "raw" / "mrf" / 'tri-city-medical-center-standardcharges.csv',
        mrf_format='csv',
        scan_scope='full_local_csv',
    ),
    LocalMrfSource(
        url_marker='95-2321136_LOS-ROBLES-HOSPITAL-AND-MEDICAL-CENTER_standardcharges.json',
        path=ROOT / "data" / "raw" / "mrf" / 'los-robles-regional-medical-center-standardcharges.json',
        mrf_format='json',
        scan_scope='large_local_json',
    ),
    LocalMrfSource(
        url_marker='951683892_community-memorial-healthcare-ventura_standardcharges.csv.csv',
        path=ROOT / "data" / "raw" / "mrf" / 'community-memorial-ventura-standardcharges.csv',
        mrf_format='csv',
        scan_scope='full_local_csv',
    ),
    LocalMrfSource(
        url_marker='951684089_Scripps-Memorial-Hospital-La-Jolla_standardcharges.csv',
        path=ROOT / "data" / "raw" / "mrf" / 'scripps-memorial-la-jolla-standardcharges.csv',
        mrf_format='csv',
        scan_scope='full_local_csv',
    ),
    LocalMrfSource(
        url_marker='951684089_Scripps-Mercy-Hospital-San-Diego_standardcharges.csv',
        path=ROOT / "data" / "raw" / "mrf" / 'scripps-mercy-san-diego-standardcharges.csv',
        mrf_format='csv',
        scan_scope='full_local_csv',
    ),
    LocalMrfSource(
        url_marker='95-3782169_sharp-memorial-hospital_standardcharges.csv',
        path=ROOT / "data" / "raw" / "mrf" / 'sharp-memorial-standardcharges.csv',
        mrf_format='csv',
        scan_scope='full_local_csv',
    ),
    LocalMrfSource(
        url_marker='33-0449527_grossmont-hospital-corporation_standardcharges.csv',
        path=ROOT / "data" / "raw" / "mrf" / 'sharp-grossmont-standardcharges.csv',
        mrf_format='csv',
        scan_scope='full_local_csv',
    ),
    LocalMrfSource(
        url_marker='205837239_ParadiseValleyHospital_standardcharges.JSON',
        path=ROOT / "data" / "raw" / "mrf" / 'paradise-valley-standardcharges.json',
        mrf_format='json',
        scan_scope='large_local_json',
    ),
)


def resolve_local_source(mrf_url: str) -> LocalMrfSource | None:
    for source in LOCAL_MRF_SOURCES:
        if source.url_marker in mrf_url and source.path.exists():
            return source
    return None
