from __future__ import annotations

import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "db" / "schema.sql"
DEFAULT_DB_PATH = ROOT / "data" / "processed" / "healthscan.sqlite"


def connect(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    connection.commit()


def upsert_hospital(
    connection: sqlite3.Connection,
    *,
    name: str,
    domain: str,
    address: str | None = None,
    state: str | None = None,
    zip_code: str | None = None,
    cms_hpt_url: str | None = None,
) -> int:
    row = connection.execute("SELECT id FROM hospitals WHERE name = ?", (name,)).fetchone()
    if row:
        hospital_id = int(row["id"])
        connection.execute(
            """
            UPDATE hospitals
            SET domain = COALESCE(?, domain),
                address = COALESCE(?, address),
                state = COALESCE(?, state),
                zip = COALESCE(?, zip),
                cms_hpt_url = COALESCE(?, cms_hpt_url)
            WHERE id = ?
            """,
            (domain, address, state, zip_code, cms_hpt_url, hospital_id),
        )
        return hospital_id

    cursor = connection.execute(
        """
        INSERT INTO hospitals (name, domain, address, state, zip, cms_hpt_url)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (name, domain, address, state, zip_code, cms_hpt_url),
    )
    return int(cursor.lastrowid)


def upsert_mrf_source(
    connection: sqlite3.Connection,
    *,
    hospital_id: int,
    source_url: str,
    content_type: str | None = None,
    content_length_bytes: int | None = None,
    mrf_format: str | None = None,
    mrf_date: str | None = None,
    status: str | None = None,
    error: str | None = None,
) -> int:
    connection.execute(
        """
        INSERT OR IGNORE INTO mrf_sources (
            hospital_id, source_url, content_type, content_length_bytes, mrf_format, mrf_date
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (hospital_id, source_url, content_type, content_length_bytes, mrf_format, mrf_date),
    )
    connection.execute(
        """
        UPDATE mrf_sources
        SET content_type = COALESCE(?, content_type),
            content_length_bytes = COALESCE(?, content_length_bytes),
            mrf_format = COALESCE(?, mrf_format),
            mrf_date = COALESCE(?, mrf_date),
            last_crawled_at = CURRENT_TIMESTAMP,
            last_status = ?,
            last_error = ?
        WHERE hospital_id = ? AND source_url = ?
        """,
        (content_type, content_length_bytes, mrf_format, mrf_date, status, error, hospital_id, source_url),
    )
    row = connection.execute(
        "SELECT id FROM mrf_sources WHERE hospital_id = ? AND source_url = ?",
        (hospital_id, source_url),
    ).fetchone()
    return int(row["id"])
