# CMS Price Transparency Validation Report

Date: 2026-06-13

## Executive Summary

HealthScan's initial validation confirms that hospital price transparency machine-readable files can be discovered and probed directly, but the approach is not reliable enough yet for a simple root-domain crawler. The viable architecture is direct MRF discovery plus scheduled background indexing, not query-time MRF fetching.

Phase 1 passed with three concrete MRF discovery examples. Phase 2 failed under root-domain `cms-hpt.txt` discovery alone, but passed after adding the manual-registry fallback: all 5 target cities reached the >70% accessible-MRF threshold. The failures were discovery-path problems, not proof that MRF data was unavailable.

## Source Basis

- Source plan: `docs/cms-research-plan.md`
- CMS technical guide: https://github.com/CMSgov/hospital-price-transparency
- CMS template documentation: https://github.com/CMSgov/hospital-price-transparency/tree/master/documentation
- CMS validator tools: https://cmsgov.github.io/hpt-tool/

CMS's official repository confirms that hospitals may publish MRFs in CSV tall, CSV wide, or JSON template formats. The 2026 rule updates add and remove required elements effective January 1, 2026, with enforcement beginning April 1, 2026.

## Phase 1 Findings

Phase 1 tested whether `cms-hpt.txt` discovery works and whether linked MRF files can be probed.

| System | Discovery Result | MRF Probe | Finding |
| --- | --- | --- | --- |
| Mayo Clinic | `https://www.mayoclinic.org/cms-hpt.txt` returned HTTP 200 | CSV-like MRF, 14,563,085,729 bytes | Discovery works, but full-file request-time fetch is not viable. |
| Cleveland Clinic | `https://my.clevelandclinic.org/cms-hpt.txt` returned HTTP 200 | `application/octet-stream`, 51,348,717 bytes | Requires subdomain fallback beyond the marketing domain. |
| NewYork-Presbyterian | `https://www.nyp.org/cms-hpt.txt` returned HTTP 200 | JSON ZIP, 3,392,675 bytes | MRF URL may include query parameters and ZIP delivery. |
| Johns Hopkins Medicine | `https://www.hopkinsmedicine.org/cms-hpt.txt` returned HTTP 403 | Not reached | Needs alternate/manual discovery due to Cloudflare blocking. |

Phase 1 result: pass, with fallback requirements.

## Phase 2 Accessibility Gate

Phase 2 sampled 15 hospitals across five target cities and checked whether each had an accessible `cms-hpt.txt` and probeable first MRF URL.

| City | Hospitals Checked | Accessible MRFs | Accessible % | Gate Result |
| --- | ---: | ---: | ---: | --- |
| New York, NY | 3 | 2 | 66.7% | fail |
| Houston, TX | 3 | 2 | 66.7% | fail |
| Minneapolis, MN | 3 | 3 | 100.0% | pass |
| Phoenix, AZ | 3 | 1 | 33.3% | fail |
| Asheville, NC | 3 | 3 | 100.0% | pass |

Strict Phase 2 gate: at least 3 of 5 cities must show >70% accessible, populated MRFs.

Initial root-domain result: preliminary fail. Only Minneapolis and Asheville exceeded the threshold. New York and Houston were close at 2/3; Phoenix was weak at 1/3.

After populating the manual registry for Mount Sinai, Banner, Dignity Health, and St. Luke's Health, the fallback-aware Phase 2 result passes:

| City | Hospitals Checked | Accessible MRFs With Fallback | Accessible % | Gate Result |
| --- | ---: | ---: | ---: | --- |
| New York, NY | 3 | 3 | 100.0% | pass |
| Houston, TX | 3 | 3 | 100.0% | pass |
| Minneapolis, MN | 3 | 3 | 100.0% | pass |
| Phoenix, AZ | 3 | 3 | 100.0% | pass |
| Asheville, NC | 3 | 3 | 100.0% | pass |

## Delivery Patterns Encountered

| Pattern | Examples | Implication |
| --- | --- | --- |
| Huge CSV | Mayo Clinic, NYU Langone, M Health Fairview | Must stream and filter; do not load full files into memory. |
| JSON ZIP | NewYork-Presbyterian | Need ZIP handling and JSON parser. |
| `.ashx` download | Houston Methodist, Memorial Hermann | Format detection must use headers/content, not extension only. |
| Extensionless endpoint | Hennepin Healthcare, Pardee Hospital | URL-based format detection is insufficient. |
| Signed Blob URL | Mission Health | URLs may be long, signed, and time-sensitive. |
| Wrapped URL | AdventHealth | Crawler must unwrap or follow redirect-wrapper links. |
| 403/404 at root | Mount Sinai, Banner, Dignity, St. Luke's, Johns Hopkins | Need source-page discovery and subdomain search. |

## Architecture Decision

Use scheduled background indexing. The public query path must not fetch hospital MRFs on demand.

The crawler should:

- Discover MRF URLs through a three-tier strategy: `cms-hpt.txt`, source-page scraping, then a curated manual registry.
- Fetch/stream MRFs out of band.
- Extract only rows matching the approved procedure-code list.
- Normalize matched prices into HealthScan's database.
- Serve user searches from the indexed database only.

This is required because a single MRF can be enormous. Mayo Clinic's Rochester file was probed at about 14.6 GB, while the MVP only needs rows for a limited procedure list.

## Internal Data Contract

The query-facing indexed record should expose:

```text
hospital_id, hospital_name, address, state, zip
procedure_code, code_type, description
price_type, amount, payer_name, plan_name
last_updated, source_url, data_quality_flag
```

The starter SQLite schema is in `db/schema.sql`. It normalizes prices as one row per `price_type` and `amount`, which is better for search, filtering, and comparison than storing many price columns per row.

## Current Risks

- Root-domain `cms-hpt.txt` discovery misses or blocks too many hospitals.
- Some HTTP clients are rejected even when browser-like fetches work.
- File sizes range from small ZIPs to multi-gigabyte CSVs.
- HEAD `content-length` can be missing or misleading.
- Phase 2 has not yet validated procedure-level row presence or price-field population.
- Cash price and negotiated-rate completeness remain unknown until stream/filter indexing is tested.

## Recommendation

Continue with direct MRF indexing, but do not start the public-facing app yet.

The discovery layer should no longer treat root-domain `cms-hpt.txt` as the primary mechanism by itself. Use it as tier one, then fall back to source-page scraping and finally a curated manual registry for high-value hospitals where automated discovery consistently fails.

The next build step should be a background indexing prototype that proves HealthScan can stream/filter real MRFs for DRG 470, DRG 807, and CPT 45378. Use one small/medium file and one large file. The success criterion should be matched-row counts and populated price fields, not just MRF accessibility.

## Next Validation Gate

Build and run a procedure-level indexing prototype:

1. Load supported codes from `data/reference/procedure_mapping.csv`.
2. Stream a CSV MRF and extract matching rows.
3. Handle at least one ZIP or extensionless download source.
4. Write normalized records to `db/schema.sql`.
5. Report counts by hospital, procedure code, price type, payer, and data quality flag.

If this succeeds on representative files, move Phase 2 from accessibility validation to populated-procedure validation.

## MVP Layer 1 Market Update

The MVP Layer 1 test market has moved from New York to Southern California, focused on Los Angeles and San Diego. The gate is now 5 or more Southern California hospitals returning plausible hip replacement prices for DRG 470.

Initial targets are tracked in `data/reference/mvp_layer1_targets.csv`; the validation plan is documented in `docs/research/mvp-layer-1-southern-california.md`.

Layer 1 result: passed. UCLA, Scripps Green, Keck Hospital of USC, Sharp Chula Vista, and UC San Diego Medical Center returned DRG 470 price rows. The local SQLite index contains 821 DRG 470 price rows across 5 hospitals. Cedars-Sinai is added as a pending large-file candidate because its server ignored byte-range requests and returned the full ~884 MB JSON.

## MVP Layer 2 Gate Update

Layer 2 result: passed. Ten of ten starter procedures now return results from more than 3 Southern California hospitals. The final coverage source was Rady Children's Hospital, whose CSV labels CPT-style rows such as 45378, 70551, 74176, and 99285 as `HCPCS`. The parser now treats HCPCS-coded rows as compatible for CPT searches when the procedure code itself matches.

The detailed evidence files are `data/research/mvp_layer2_gate_summary.csv` and `docs/research/mvp-layer-2-southern-california.md`.

## MVP Layer 3 Gate Update

Layer 3 result: passed. The normalization runner produced `data/processed/layer3_search_results.csv` with 42 search-ready display rows. Ten of ten starter procedures have search-ready prices from at least 3 Southern California hospitals.

The pass required handling three real-world normalization cases:

- DRG 470 must be materialized for both hip replacement and knee replacement in the starter mapping.
- Some CPT-style rows are labeled `HCPCS`, especially in the Rady Children's Hospital CSV.
- Hospital CSV exports shift payer and price columns, so the parser needs source-shape detection.
- UCSD-style JSON snippets can provide search-ready prices for procedures that are present in Layer 2 but not yet fully indexed.

The next implementation target should replace byte-offset JSON evidence with a proper streaming parser for large UCSD-style JSON MRFs.

## Procedure Translation Layer Update

The baseline translation layer is implemented in `src/healthscan/translation.py`. It resolves plain-language procedure inputs to CMS-engine-compatible `procedure_code` and `code_type` values, supports DRG and CPT/HCPCS code paths, returns multiple candidates for ambiguous inputs, and fails gracefully for unrecognized inputs.

The external-model fallback is provider-agnostic. Any future Claude, OpenAI, or other provider adapter must return structured candidates with `code`, `code_type`, `plain_label`, and `confidence`; free-text answers are rejected.

Validation result: `scripts/run_translation_validation.py` passes 50 of 50 regression cases, including 30 exact mapping cases, 10 synonym/layperson variants, 5 ambiguous inputs, and 5 invalid inputs. Exact-match accuracy is 30 of 30, and lookup-table responses are under the 100ms target.

## MVP Layer 4 Expansion Update

Layer 4 scan-engine expansion has started. The first repeatable audit tracks 25 Southern California hospitals in `data/reference/layer4_hospital_targets.csv` and writes results to `data/research/layer4_scan_engine_audit.csv`.

Current audit result:

- 25 target hospitals
- 10 known MRF/source URLs
- 9 hospitals already search-ready from prior layers
- 1 known source needing indexing
- 15 hospitals needing source discovery
- 8 priority 1 hospitals already search-ready

The immediate hardening target is Cedars-Sinai: its MRF URL is known, but previous testing showed range requests were not useful, so it needs a streaming/full-file JSON parser path. The broader expansion target is source discovery for Kaiser, CHLA, City of Hope, Hoag, MemorialCare, Palomar, and other missing-source hospitals.

The South California full functionality test is implemented in `scripts/run_socal_functionality_test.py`. It validates the current product path from plain-language query through translation and schema-compatible code lookup into South California search-ready rows. Current combined result: 30 exact translated procedure queries were tested, all 30 returned South California results, all 30 had 3 or more hospital results, and 0 need indexing expansion before returning prices.

The large-JSON parser scaffold is implemented in `src/healthscan/streaming_json.py` and covered by tests. It is ready to apply to Cedars-Sinai once the MRF is available through the crawler/cache path.

The indexing expansion queue is now explicit. The South California no-result functionality rows produce `data/research/indexing_expansion_worklist.csv` with 20 procedures and 33 code targets. `scripts/build_layer4_scan_matrix.py` expands that into `data/research/layer4_scan_matrix.csv`, currently 330 queued scan jobs across 10 known-source hospitals.

The local scan batch executed the expansion codes against local MRF artifacts, including full Scripps, Keck, UCSD, Sharp, Cedars-Sinai, UCLA, and Rady files. It processed 231 local jobs, matched 209 jobs, and generated 14,355 search-ready rows. Merging those rows with Layer 3 produces `data/processed/combined_search_results.csv` with 14,089 rows.

Expanded South California functionality result: all 30 exact translated procedures now return at least one South California price result, and all 30 have 3 or more hospital results. `data/research/layer4_breadth_gap.csv` is empty beyond its header, and `data/research/layer4_breadth_gap_summary.csv` reports 0 additional hospital matches needed.

Layer 4 result: passed for the current 30-procedure Southern California MVP scope.

The patient-facing quality filter is now implemented. Search rows retain the original `data_quality_flag`, add `user_relevance_flag` and `user_relevance_reason`, and default searches suppress rows with implausible or non-informative quality flags. Current excluded flags are `low_outlier`, `high_outlier`, and `placeholder_amount`.

Quality-filter audit result: 14,089 combined rows, 10,833 patient-facing display rows, and 3,256 filtered rows. All filtered rows in this run are `excluded_low_outlier`. The filtered South California functionality gate still passes with all 30 exact translated procedures returning results from 3 or more hospitals.
