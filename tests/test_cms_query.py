from __future__ import annotations

from pathlib import Path

from healthscan.cms_query import search_indexed_prices
from healthscan.database import connect, initialize, upsert_hospital, upsert_mrf_source


def workspace_tmp_path(name: str) -> Path:
    path = Path("data") / "tmp" / "tests" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    return path


def insert_price(
    connection,
    *,
    hospital_id: int,
    source_id: int,
    procedure_name: str,
    procedure_code: str,
    code_type: str,
    setting: str,
    price_type: str,
    amount: float,
) -> None:
    connection.execute(
        """
        INSERT INTO indexed_prices (
            hospital_id, mrf_source_id, procedure_name, procedure_code, code_type,
            description, setting, price_type, amount, source_url, data_quality_flag
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            hospital_id,
            source_id,
            procedure_name,
            procedure_code,
            code_type,
            procedure_name,
            setting,
            price_type,
            amount,
            "https://example.org/mrf.csv",
            "ok",
        ),
    )


def build_indexed_db(name: str) -> Path:
    db_path = workspace_tmp_path(name)

    connection = connect(db_path)
    try:
        initialize(connection)
        alpha_id = upsert_hospital(connection, name="Alpha Hospital", domain="alpha.example")
        beta_id = upsert_hospital(connection, name="Beta Hospital", domain="beta.example")
        alpha_source = upsert_mrf_source(connection, hospital_id=alpha_id, source_url="https://alpha.example/mrf.csv")
        beta_source = upsert_mrf_source(connection, hospital_id=beta_id, source_url="https://beta.example/mrf.csv")
        insert_price(
            connection,
            hospital_id=alpha_id,
            source_id=alpha_source,
            procedure_name="Knee replacement DRG",
            procedure_code="470",
            code_type="DRG",
            setting="inpatient",
            price_type="cash",
            amount=25000,
        )
        insert_price(
            connection,
            hospital_id=alpha_id,
            source_id=alpha_source,
            procedure_name="Knee replacement CPT",
            procedure_code="27447",
            code_type="CPT",
            setting="outpatient",
            price_type="negotiated",
            amount=18000,
        )
        insert_price(
            connection,
            hospital_id=beta_id,
            source_id=beta_source,
            procedure_name="Knee replacement",
            procedure_code="470",
            code_type="DRG",
            setting="inpatient",
            price_type="cash",
            amount=21000,
        )
        connection.commit()
    finally:
        connection.close()
    return db_path


def test_search_indexed_prices_or_queries_multiple_codes_and_dedupes_hospitals() -> None:
    db_path = build_indexed_db("cms-query-dedupe.sqlite")

    status, hits = search_indexed_prices("knee replacement", db_path=db_path)

    assert status == "ok"
    assert [hit.hospital for hit in hits] == ["Alpha Hospital", "Beta Hospital"]
    assert hits[0].procedure_code == "27447"
    assert hits[0].code_type == "CPT"
    assert hits[0].setting == "outpatient"
    assert hits[1].procedure_code == "470"


def test_search_indexed_prices_returns_index_gap_for_valid_translation_without_rows() -> None:
    db_path = build_indexed_db("cms-query-gap.sqlite")

    status, hits = search_indexed_prices("screening colonoscopy", db_path=db_path)

    assert status == "no_indexed_hospitals_for_code"
    assert hits == []


def test_search_indexed_prices_passes_through_clarification_status() -> None:
    db_path = build_indexed_db("cms-query-clarify.sqlite")

    status, hits = search_indexed_prices("heart surgery", db_path=db_path)

    assert status == "ambiguous"
    assert hits == []
