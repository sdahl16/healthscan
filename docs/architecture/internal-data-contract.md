# Internal Data Contract

This is the canonical query-facing shape for procedure price records after background indexing. It intentionally stores one price per row so the search layer does not need to understand the source MRF's original wide/tall/JSON layout.

## Hospital Fields

| Field | Source Table | Notes |
| --- | --- | --- |
| hospital_id | `hospitals.id` | Internal primary key |
| hospital_name | `hospitals.name` | Display name |
| address | `hospitals.address` | Street address when available |
| state | `hospitals.state` | Two-letter state code when available |
| zip | `hospitals.zip` | ZIP or ZIP+4 when available |

## Procedure Fields

| Field | Source Table | Notes |
| --- | --- | --- |
| procedure_code | `indexed_prices.procedure_code` | Matched billing code |
| code_type | `indexed_prices.code_type` | DRG, CPT, HCPCS, APC, RC, etc. |
| description | `indexed_prices.description` | Hospital-provided service description |

## Price Fields

| Field | Source Table | Notes |
| --- | --- | --- |
| price_type | `indexed_prices.price_type` | `gross`, `cash`, `negotiated`, `negotiated_min`, `negotiated_max`, `median_allowed`, `allowed_p10`, or `allowed_p90` |
| amount | `indexed_prices.amount` | Numeric price/amount for the row |
| payer_name | `indexed_prices.payer_name` | Required for payer-specific negotiated rows when present |
| plan_name | `indexed_prices.plan_name` | Required for plan-specific negotiated rows when present |

## Provenance & Quality

| Field | Source Table | Notes |
| --- | --- | --- |
| last_updated | `indexed_prices.last_updated` | Prefer MRF date; fall back to crawl/parse timestamp |
| source_url | `indexed_prices.source_url` | MRF URL that produced the row |
| data_quality_flag | `indexed_prices.data_quality_flag` | Examples: `ok`, `missing_cash_price`, `placeholder_amount`, `schema_unknown`, `stale_source` |

## Query View

A future SQL view can expose exactly these fields by joining `indexed_prices` to `hospitals`.
