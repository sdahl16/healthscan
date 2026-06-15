# Background Procedure Indexing

HealthScan should not fetch hospital MRFs during user searches. MRF acquisition and parsing should happen in a scheduled background job that creates a small, query-ready dataset.

## Rationale

Phase 1 found that valid MRFs can vary from a few megabytes to many gigabytes. Mayo Clinic's Rochester MRF probe returned a content length of 14,563,085,729 bytes. Since the MVP only supports a curated set of procedures, most rows in a full MRF are irrelevant to search.

The correct product architecture is to pay the ingestion cost once in the background, filter aggressively by known codes, and serve users from HealthScan's own normalized index.

## Flow

1. Discover hospital MRF URLs from `cms-hpt.txt`.
2. Store source metadata and enqueue crawl work.
3. Background worker downloads or streams each MRF.
4. Parser detects CSV tall, CSV wide, JSON, ZIP, GZIP, or unknown format.
5. Parser extracts only rows whose `code_type` and `code` match the supported procedure list.
6. Normalizer writes matched rows to the database.
7. Search API reads only from the normalized database.

## Minimal Indexed Record

| Field | Purpose |
| --- | --- |
| hospital_id | Link result to hospital identity |
| hospital_name | Display fallback |
| address | Hospital street address |
| state | Hospital state |
| zip | Hospital ZIP code |
| source_mrf_url | Auditability |
| source_mrf_date | Freshness indicator |
| procedure_name | User-facing grouped label |
| procedure_code | Billing code matched |
| code_type | DRG, CPT, HCPCS, APC, etc. |
| description | Hospital-provided row description |
| setting | inpatient, outpatient, or unknown |
| price_type | Gross, cash, negotiated, negotiated min, negotiated max, or allowed amount statistic |
| amount | Numeric value for this price row |
| payer_name | Negotiated rate context |
| plan_name | Negotiated rate context |
| allowed_amount_count | 2026 count field when present |
| last_updated | Prefer MRF date; fall back to crawl timestamp |
| source_url | Original MRF URL |
| data_quality_flag | Search/filter hint for questionable records |
| parsed_at | Index freshness |
| parse_warnings | Data quality notes |

See `docs/architecture/internal-data-contract.md` for the canonical query-facing schema.

## Immediate Prototype Tasks

- Build a streaming CSV filter for `procedure_mapping.csv`.
- Add ZIP input handling without extracting huge archives to disk.
- Use `db/schema.sql` as the first SQLite schema for indexed procedure rows and crawl metadata.
- Test the filter on one small MRF first, then on a large file with a row limit or byte limit.
- Record matched-row counts per hospital to support Phase 2 quality scoring.
