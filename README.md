# HealthScan

HealthScan is a research-first project for evaluating whether CMS Hospital Price Transparency machine-readable files can power a patient-facing hospital price comparison tool.

The current milestone is Phase 1 from `docs/cms-research-plan.md`: understand the 2026 CMS MRF schema, verify `cms-hpt.txt` discovery on real hospitals, and document enough data quality evidence to decide whether a direct MRF pipeline is viable.

## Current Scope

- Project context and safety boundaries: `CONTEXT.md`
- Source plan: `docs/cms-research-plan.md`
- Consolidated validation report: `docs/reports/cms-price-transparency-validation-report.md`
- Phase 1 research log: `docs/research/phase-1-schema-and-discovery.md`
- Phase 1 validation evidence: `data/research/phase1_validation_instances.csv`
- Background indexing architecture: `docs/architecture/background-indexing.md`
- Discovery strategy: `docs/architecture/discovery-strategy.md`
- Internal data contract: `docs/architecture/internal-data-contract.md`
- Procedure translation layer: `docs/architecture/procedure-translation-layer.md`
- City sampling template: `docs/research/phase-2-city-sampling.md`
- Phase 2 gate record: `docs/research/phase-2-gate.md`
- MVP Layer 1 Southern California plan: `docs/research/mvp-layer-1-southern-california.md`
- MVP Layer 2 Southern California plan: `docs/research/mvp-layer-2-southern-california.md`
- MVP Layer 3 search normalization plan: `docs/research/mvp-layer-3-search-normalization.md`
- MVP Layer 4 scan engine expansion plan: `docs/research/mvp-layer-4-scan-engine-expansion.md`
- Starter hospital targets: `data/reference/hospital_targets.csv`
- MVP Layer 1 targets: `data/reference/mvp_layer1_targets.csv`
- Starter procedure/code map: `data/reference/procedure_mapping.csv`
- Starter indexing schema: `db/schema.sql`
- Discovery code: `src/healthscan/discovery.py`

## Phase Gates

1. Phase 1 passes when `cms-hpt.txt` discovery works on 3 of 3 initial hospitals and each discovered MRF can be downloaded and classified.
2. Phase 2 passes when at least 3 of 5 sampled cities show more than 70 percent of hospitals with accessible, populated MRFs.
3. Public search must query HealthScan's own indexed database, not hospital MRFs directly.
4. Build work should stay scoped to research tools until the data approach is chosen in `docs/architecture/decision-log.md`.

## Quick Start

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest
```

Run a local discovery check:

```powershell
python -m healthscan.cli discover https://example.org/cms-hpt.txt
```

The discovery command accepts either a hospital domain such as `https://example.org` or a direct `cms-hpt.txt` URL.

## Current Validation Snapshot

Phase 1 has three successful discovery instances: Mayo Clinic, Cleveland Clinic via `my.clevelandclinic.org`, and NewYork-Presbyterian. Johns Hopkins returned a Cloudflare 403 from this environment and should be revisited with manual/browser-based discovery.

Mayo's discovered Rochester MRF is about 14.6 GB, so background indexing is now the default architecture constraint: scheduled jobs should stream MRFs, extract only supported procedure-code rows, and store those normalized records for instant database-backed search.

Phase 2 accessibility failed with root-domain `cms-hpt.txt` alone, but passed after adding manual-registry fallback URLs for the failed high-value systems. The next validation step is procedure-level stream/filter indexing.

MVP Layer 1 testing has moved from New York to Southern California, focused on Los Angeles and San Diego. The gate is 5 or more Southern California hospitals returning plausible DRG 470 hip replacement prices.

Layer 1 has passed. The local SQLite index at `data/processed/healthscan.sqlite` contains DRG 470 prices for 5 Southern California hospitals and 821 indexed price rows.

Layer 2 has passed. Ten of ten starter procedures now return results from more than 3 Southern California hospitals after adding alternate-code scans, Providence sources, UCSD offsets, and Rady Children's Hospital rows. Rady labels several CPT-style procedure rows as `HCPCS`, so CPT searches now accept compatible HCPCS-coded rows.

Layer 3 has passed. The search normalization export at `data/processed/layer3_search_results.csv` contains 42 display-ready rows, and 10 of 10 starter procedures have search-ready prices from at least 3 hospitals. The next hardening step is replacing byte-offset JSON snippets with streaming full-MRF parsers for UCSD-style files.

The baseline procedure translation layer is implemented. `scripts/run_translation_validation.py` covers 30 exact mapping cases, 10 synonym/layperson cases, 5 ambiguous inputs, and 5 invalid inputs. Current result: 50/50 validation cases pass, with 30/30 exact-match accuracy and lookup-table latency under 100ms.

Layer 4 expansion has started. The first scan-engine audit tracks 25 Southern California hospitals, with 10 known source URLs, 9 search-ready hospitals, 1 known source needing indexing, and 15 hospitals needing source discovery. Cedars-Sinai is the main priority parser-hardening target.

The South California full functionality test is implemented. It runs plain-language query -> translation -> schema-compatible code lookup -> South California search-ready rows. Current combined result: all 30 translated procedures return South California prices, and all 30 have 3+ hospital breadth.

The indexing expansion queue is generated. `data/research/indexing_expansion_worklist.csv` contains 20 procedures and 33 code targets needing South California indexing. `data/research/layer4_scan_matrix.csv` expands those into 330 queued hospital/code scan jobs across 10 known-source hospitals.

The local scan batch now includes full Scripps, Keck, UCSD, Sharp, Cedars-Sinai, UCLA, and Rady artifacts, with large local JSON and optional alternate-code scans enabled. The latest alternate-inclusive run executed 231 jobs, matched 209 jobs, and generated 14,355 search-ready rows. After merging with Layer 3, `data/processed/combined_search_results.csv` contains 14,089 rows. `data/research/layer4_breadth_gap.csv` is empty beyond its header, so the Layer 4 breadth gate is now closed.

The patient-facing quality filter is implemented. Search results now carry `user_relevance_flag` and `user_relevance_reason`, and normal searches hide rows with implausible `data_quality_flag` values such as `low_outlier`. The latest audit keeps 10,833 display rows and filters 3,256 low-outlier rows; the filtered South California functionality gate still passes with 30 of 30 procedures returning 3+ hospitals.
