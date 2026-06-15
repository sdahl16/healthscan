# HealthScan Project Context

HealthScan is a research-first medical price transparency project. It explores whether CMS Hospital Price Transparency machine-readable files (MRFs) can be normalized into a patient-facing search experience for common procedures.

## Product intent

- Help users compare hospital-published standard charges for common procedures.
- Start with Southern California hospitals and a curated procedure/code set.
- Serve search from a local indexed database or generated search-ready artifacts, not by querying live hospital MRFs during user requests.
- Keep raw multi-GB MRF artifacts local and out of git.

## Medical and financial safety boundaries

HealthScan is informational only. It does not provide medical advice, diagnosis, treatment recommendations, insurance guidance, or a guarantee of out-of-pocket cost.

User-facing copy should preserve these points:

- Hospital standard charges are not the same as what an insured patient will pay.
- Actual cost depends on payer, plan, deductible, network status, coding, clinical circumstances, and hospital billing practices.
- Data comes from hospital-published CMS machine-readable files and may lag current pricing.
- Users should confirm estimates with the hospital and insurer before scheduling care.

## Current architecture

- `src/healthscan/discovery.py`: `cms-hpt.txt` and MRF discovery utilities.
- `src/healthscan/indexer.py`: extracts targeted procedure-code rows from MRF records.
- `src/healthscan/streaming_json.py`: streaming parser support for large JSON MRFs.
- `src/healthscan/translation.py`: plain-language procedure translation into CPT/HCPCS/DRG targets.
- `src/healthscan/cms_query.py`: indexed-price query path for frontend/API usage.
- `src/healthscan/relevance.py`: patient-facing relevance and quality filtering.
- `public/`: lightweight static frontend.
- `scripts/frontend_server.py`: local development server for the frontend/API.
- `db/schema.sql`: intended SQLite schema for normalized indexed prices.

## Important data policy

Git tracks lightweight reference, research, documentation, source, and test files. Git intentionally ignores large/generated artifacts:

- `data/raw/` — raw downloaded MRF files, often hundreds of MB to multiple GB.
- `data/processed/` — generated SQLite and combined search exports.
- `data/tmp/` — temporary test/work files.
- `.secrets/` and fallback logs.

If generated outputs are needed, recreate them locally with the scripts rather than committing large data files.

## Validation commands

Run the full Python test suite from the repository root:

```bash
PYTHONPATH=src python3 -m pytest
```

Run translation validation:

```bash
PYTHONPATH=src python3 scripts/run_translation_validation.py
```

Run the local frontend server:

```bash
python3 scripts/frontend_server.py
```

## Current status snapshot

- Southern California is the active launch geography.
- The current translation validation set covers exact names, synonyms, ambiguous inputs, and invalid inputs.
- Layer 4 breadth gate is closed in the latest local research outputs: 30/30 tracked procedures have 3+ hospital breadth after the full local scan/combined search pipeline.
- Patient-facing filtering suppresses known implausible rows such as `low_outlier` by default.
