# MVP Layer 4 - Scan Engine Expansion

Status: passed

## Gate

Layer 4 should prove the CMS scan engine can expand beyond the initial hand-worked hospital set.

Proposed pass gate:

- 15 to 25 Southern California hospitals are tracked in a repeatable target list.
- At least 80 percent of priority 1 hospitals have search-ready rows.
- At least 15 hospitals have known MRF source URLs.
- At least 12 hospitals have search-ready rows for one or more starter procedures.
- Failures are categorized as discovery failure, source known but parser/indexing missing, or already search-ready.

## Target List

Target file: `data/reference/layer4_hospital_targets.csv`

The first Layer 4 cohort contains 25 hospitals across:

- Los Angeles
- Orange County
- Inland Empire
- San Diego

## Audit Outputs

- Runner: `scripts/run_layer4_scan_engine_audit.py`
- Audit CSV: `data/research/layer4_scan_engine_audit.csv`
- Summary CSV: `data/research/layer4_scan_engine_summary.csv`
- South California functionality runner: `scripts/run_socal_functionality_test.py`
- South California functionality output: `data/research/socal_functionality_results.csv`
- Indexing expansion worklist: `data/research/indexing_expansion_worklist.csv`
- Layer 4 scan matrix: `data/research/layer4_scan_matrix.csv`
- Local scan batch runner: `scripts/run_layer4_local_scan_batch.py`
- Local scan batch output: `data/research/layer4_local_scan_results.csv`
- Combined search export: `data/processed/combined_search_results.csv`
- Breadth gap report: `data/research/layer4_breadth_gap.csv`

## First Audit Result

Current snapshot:

| Metric | Count |
| --- | ---: |
| Target hospitals | 25 |
| Known MRF/source URLs | 10 |
| Search-ready hospitals | 9 |
| Source known, needs indexing | 1 |
| Needs discovery | 15 |
| Priority 1 search-ready hospitals | 8 |

Priority 1 coverage is already strong because UCLA, Keck, Providence Tarzana, Providence Holy Cross, Providence Saint Joseph, UCSD, Scripps, and Sharp have search-ready evidence. Cedars-Sinai is the main priority 1 gap: its MRF URL is known, but prior testing showed it requires full-file or streaming JSON parsing because byte ranges were not honored.

## Next Actions

1. Tighten data-quality filtering for implausibly low prices before public presentation.
2. Add source discovery runs for the 15 missing-source hospitals:
   - Kaiser Permanente Los Angeles Medical Center
   - Children's Hospital Los Angeles
   - City of Hope Medical Center
   - Huntington Hospital
   - Torrance Memorial Medical Center
   - PIH Health Good Samaritan Hospital
   - UCI Medical Center
   - Hoag Hospital Newport Beach
   - MemorialCare Orange Coast Medical Center
   - Loma Linda University Medical Center
   - Riverside Community Hospital
   - Palomar Medical Center Escondido
   - Kaiser Permanente San Diego Medical Center
   - Tri-City Medical Center
   - Alvarado Hospital Medical Center
3. Promote source URLs discovered through Layer 3 evidence into the manual registry once verified from official pages.
4. Expand regression checks so each search-ready hospital is re-tested through translation -> code lookup -> indexed/search-ready rows.

## Interpretation

Layer 4 is now a repeatable expansion audit and a passed indexing breadth gate for the current Southern California MVP scope. It shows the remaining work clearly:

- discovery expansion for missing-source hospitals
- data-quality filtering for implausible prices
- regression coverage for already search-ready hospitals

## Streaming JSON Parser Scaffold

The first large-JSON hardening path is implemented in `src/healthscan/streaming_json.py`. It scans large JSON text in chunks, finds code matches, anchors on the enclosing described charge item, and sends those fragments through the existing JSON-fragment normalizer.

This has now been applied to local UCLA, UCSD, and Cedars-Sinai-style large JSON files through the Layer 4 local scan batch.

## South California Functionality Test

The South California functionality test exercises the current product path:

plain-language query -> translation layer -> schema-compatible code candidates -> South California search-ready rows

Baseline result before the Layer 4 indexing expansion batch:

| Metric | Count |
| --- | ---: |
| Exact procedure queries | 30 |
| Queries with South California results | 10 |
| Queries with 3+ hospital results | 10 |
| Queries needing indexing expansion | 20 |

Gate scope: original 10 indexed starter procedures. Result: pass for the Layer 3 starter set.

The remaining 20 exact mapping procedures already translated correctly, but needed scan-engine indexing before they could return South California prices. The local scan batch below closed this no-result gap.

## Indexing Expansion Queue

The functionality no-result rows now generate a code-level indexing worklist:

- Worklist builder: `scripts/build_indexing_expansion_worklist.py`
- Worklist output: `data/research/indexing_expansion_worklist.csv`
- Procedures needing indexing: 20
- Code targets: 33
- Primary code targets: 20

The Layer 4 scan matrix pairs those code targets against known-source/search-ready hospitals:

- Matrix builder: `scripts/build_layer4_scan_matrix.py`
- Matrix output: `data/research/layer4_scan_matrix.csv`
- Queued scan jobs: 330
- Hospitals in matrix: 10
- Code targets in matrix: 33

This matrix is the next execution queue for the scan engine. Each row is one hospital/MRF/code target combination with `scan_status=queued`.

## Local Scan Batch

The bounded execution now runs expansion codes against local MRF artifacts, including large local JSON files when `--include-large-json` is provided. Alternate codes can be included with `--include-alternates`.

Current local batch result:

| Metric | Count |
| --- | ---: |
| Local scan jobs | 231 |
| Matched jobs | 209 |
| Search-ready rows generated | 14,355 |

The executor scans each local CSV once against all queued targets for that file and uses grouped code scanning for local JSON. This keeps the batch repeatable while allowing full local MRF artifacts such as UCLA, UCSD, and Cedars-Sinai JSON exports to contribute rows.

The local batch output was merged with Layer 3 results into `data/processed/combined_search_results.csv`, producing 14,089 combined search rows.

## Expanded South California Functionality Test

The combined export changes the full-path result:

| Metric | Count |
| --- | ---: |
| Exact procedure queries | 30 |
| Queries with South California results | 30 |
| Queries with 3+ hospital results | 30 |
| Queries needing indexing expansion | 0 |

Interpretation: every translated procedure now has South California price results from at least 3 hospitals. The breadth gap report is generated by `scripts/build_layer4_breadth_gap_report.py`; current output `data/research/layer4_breadth_gap.csv` is empty beyond its header, and `data/research/layer4_breadth_gap_summary.csv` reports 0 additional hospital matches needed.

Layer 4 is now a pass for the current 30-procedure Southern California MVP scope.

## Patient-Facing Quality Filter

Search results now carry:

- `data_quality_flag`: indexing-level signal such as `ok`, `low_outlier`, `high_outlier`, or `placeholder_amount`
- `user_relevance_flag`: presentation-level signal such as `display_ok` or `excluded_low_outlier`
- `user_relevance_reason`: short explanation for excluded rows

Default search behavior excludes rows that are not useful for patient-facing display while preserving them in the raw combined export for audit. The current exclusion set is:

- `low_outlier`
- `high_outlier`
- `placeholder_amount`

Current quality-filter audit:

| Metric | Count |
| --- | ---: |
| Combined rows | 14,089 |
| Patient-facing display rows | 10,833 |
| Filtered rows | 3,256 |
| Filtered percent | 23.1% |

All filtered rows in this run are `excluded_low_outlier`. After filtering, the South California functionality gate still passes: 30 of 30 exact procedure queries return results, and 30 of 30 have 3+ hospital breadth.

Audit outputs:

- Summary: `data/research/quality_filter_summary.csv`
- Procedure detail: `data/research/quality_filter_by_procedure.csv`
