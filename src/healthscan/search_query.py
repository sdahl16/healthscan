from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from healthscan.relevance import assess_price_relevance
from healthscan.translation import ProcedureTranslator


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SEARCH_RESULTS_PATH = ROOT / "data" / "processed" / "layer3_search_results.csv"


@dataclass(frozen=True)
class SearchHit:
    hospital: str
    procedure_name: str
    code_type: str
    code: str
    display_price: float
    display_price_type: str
    payer_name: str | None
    plan_name: str | None
    data_quality_flag: str
    user_relevance_flag: str
    user_relevance_reason: str | None
    source_url: str | None


def _matches_code(row: dict[str, str], *, code_type: str, code: str) -> bool:
    found_type = row["code_type"].upper()
    wanted_type = code_type.upper()
    if wanted_type == "DRG" and found_type in {"MS-DRG", "MSDRG"}:
        found_type = "DRG"
    if wanted_type == "CPT" and found_type == "HCPCS":
        found_type = "CPT"
    return found_type == wanted_type and row["code"] == code


def search_prices(
    query: str,
    *,
    care_setting: str = "unknown",
    area: str = "southern_california",
    path: Path = DEFAULT_SEARCH_RESULTS_PATH,
    translator: ProcedureTranslator | None = None,
    include_filtered: bool = False,
) -> tuple[str, list[SearchHit]]:
    if area.lower() not in {"southern_california", "south california", "socal"}:
        return "not_supported_area", []

    translator = translator or ProcedureTranslator()
    translation = translator.translate(query, care_setting=care_setting)  # type: ignore[arg-type]
    if translation.status != "match":
        return translation.status, []

    codes = translation.candidates[0].codes
    hits: list[SearchHit] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if not any(_matches_code(row, code_type=code.code_type, code=code.procedure_code) for code in codes):
                continue
            relevance = assess_price_relevance(row)
            if not include_filtered and not relevance.is_user_relevant:
                continue
            hits.append(
                SearchHit(
                    hospital=row["hospital"],
                    procedure_name=row["procedure_name"],
                    code_type=row["code_type"],
                    code=row["code"],
                    display_price=float(row["display_price"]),
                    display_price_type=row["display_price_type"],
                    payer_name=row["payer_name"] or None,
                    plan_name=row["plan_name"] or None,
                    data_quality_flag=row["data_quality_flag"],
                    user_relevance_flag=relevance.user_relevance_flag,
                    user_relevance_reason=relevance.user_relevance_reason,
                    source_url=row["source_url"] or None,
                )
            )
    hits.sort(key=lambda hit: hit.display_price)
    return "ok" if hits else "no_results", hits
