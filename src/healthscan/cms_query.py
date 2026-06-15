from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from healthscan.database import DEFAULT_DB_PATH, connect
from healthscan.relevance import assess_price_relevance
from healthscan.translation import ProcedureCode, ProcedureTranslator


CmsQueryStatus = str


@dataclass(frozen=True)
class CmsPriceHit:
    hospital_id: int
    hospital: str
    procedure_name: str
    procedure_code: str
    code_type: str
    description: str | None
    setting: str | None
    display_price: float
    display_price_type: str
    payer_name: str | None
    plan_name: str | None
    data_quality_flag: str
    user_relevance_flag: str
    user_relevance_reason: str | None
    source_url: str


PRICE_TYPE_RANK = {
    "negotiated": 1,
    "cash": 2,
    "negotiated_min": 3,
    "median_allowed": 4,
    "gross": 5,
}


def _type_matches_sql(codes: tuple[ProcedureCode, ...]) -> tuple[str, list[str]]:
    if not codes:
        return "0", []
    clauses = []
    params: list[str] = []
    for code in codes:
        clauses.append("(UPPER(p.code_type) = ? AND p.procedure_code = ?)")
        params.extend([code.code_type, code.procedure_code])
    return " OR ".join(clauses), params


def _row_to_hit(row: sqlite3.Row) -> CmsPriceHit:
    relevance = assess_price_relevance({"data_quality_flag": row["data_quality_flag"] or "ok"})
    return CmsPriceHit(
        hospital_id=int(row["hospital_id"]),
        hospital=row["hospital"],
        procedure_name=row["procedure_name"],
        procedure_code=row["procedure_code"],
        code_type=row["code_type"],
        description=row["description"],
        setting=row["translation_setting"] or row["setting"],
        display_price=float(row["amount"]),
        display_price_type=row["price_type"],
        payer_name=row["payer_name"],
        plan_name=row["plan_name"],
        data_quality_flag=row["data_quality_flag"] or "ok",
        user_relevance_flag=relevance.user_relevance_flag,
        user_relevance_reason=relevance.user_relevance_reason,
        source_url=row["source_url"],
    )


def _dedupe_by_hospital(rows: list[CmsPriceHit]) -> list[CmsPriceHit]:
    best: dict[int, CmsPriceHit] = {}
    for hit in rows:
        current = best.get(hit.hospital_id)
        if current is None:
            best[hit.hospital_id] = hit
            continue
        current_rank = PRICE_TYPE_RANK.get(current.display_price_type, 99)
        hit_rank = PRICE_TYPE_RANK.get(hit.display_price_type, 99)
        if (hit_rank, hit.display_price) < (current_rank, current.display_price):
            best[hit.hospital_id] = hit
    return sorted(best.values(), key=lambda item: item.display_price)


def query_indexed_prices_for_codes(
    connection: sqlite3.Connection,
    codes: tuple[ProcedureCode, ...],
    *,
    include_filtered: bool = False,
) -> list[CmsPriceHit]:
    where_sql, params = _type_matches_sql(codes)
    translation_setting_sql = "CASE " + " ".join(
        "WHEN UPPER(p.code_type) = ? AND p.procedure_code = ? THEN ?" for _ in codes
    ) + " END"
    setting_params: list[str] = []
    for code in codes:
        setting_params.extend([code.code_type, code.procedure_code, code.setting])

    rows = connection.execute(
        f"""
        SELECT
            p.hospital_id,
            h.name AS hospital,
            p.procedure_name,
            p.procedure_code,
            p.code_type,
            p.description,
            p.setting,
            {translation_setting_sql} AS translation_setting,
            p.price_type,
            p.amount,
            p.payer_name,
            p.plan_name,
            p.data_quality_flag,
            p.source_url
        FROM indexed_prices p
        JOIN hospitals h ON h.id = p.hospital_id
        WHERE ({where_sql})
        ORDER BY
            p.hospital_id,
            CASE p.price_type
                WHEN 'negotiated' THEN 1
                WHEN 'cash' THEN 2
                WHEN 'negotiated_min' THEN 3
                WHEN 'median_allowed' THEN 4
                WHEN 'gross' THEN 5
                ELSE 6
            END,
            p.amount
        """,
        (*setting_params, *params),
    ).fetchall()

    hits = [_row_to_hit(row) for row in rows]
    if not include_filtered:
        hits = [hit for hit in hits if hit.user_relevance_flag == "display_ok"]
    return _dedupe_by_hospital(hits)


def search_indexed_prices(
    query: str,
    *,
    db_path: Path = DEFAULT_DB_PATH,
    setting: str = "unknown",
    translator: ProcedureTranslator | None = None,
    include_filtered: bool = False,
) -> tuple[CmsQueryStatus, list[CmsPriceHit]]:
    translator = translator or ProcedureTranslator()
    translation = translator.translate(query, care_setting=setting)  # type: ignore[arg-type]
    if translation.status != "match":
        return translation.status, []
    if not translation.candidates or not translation.candidates[0].codes:
        return "procedure_not_found", []

    connection = connect(db_path)
    try:
        hits = query_indexed_prices_for_codes(
            connection,
            translation.candidates[0].codes,
            include_filtered=include_filtered,
        )
    finally:
        connection.close()
    return ("ok" if hits else "no_indexed_hospitals_for_code"), hits
