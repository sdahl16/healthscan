# MRF group quality comparison — first local group vs next-10 expansion

Date: 2026-06-17

## Scope

Compared the next-10 hospital MRF expansion against the first local full-MRF group to verify that the indexed output quality and downstream format are consistent enough to continue expanding data.

First local group used for comparison:

- Cedars-Sinai Medical Center
- Keck Hospital of USC
- Rady Children's Hospital
- Ronald Reagan UCLA Medical Center
- Scripps Green Hospital
- Sharp Chula Vista Medical Center
- UC San Diego Medical Center

Next-10 group:

- Hollywood Presbyterian Medical Center
- Huntington Hospital
- UCI Medical Center
- Hoag Hospital Newport Beach
- MemorialCare Orange Coast Medical Center
- Loma Linda University Medical Center
- Riverside Community Hospital
- Tri-City Medical Center
- Los Robles Regional Medical Center
- Community Memorial Healthcare - Ventura

## Verdict

The next-10 data is **format-consistent and usable** with the existing HealthScan pipeline. It is slightly less dense than the first group, but that looks like real source variation rather than a parser failure.

The main consistency issue found was not in the indexed price rows. It was in the frontend location layer: several new hospitals had indexed rows but lacked coordinates/address fallbacks, so they could be skipped by location-radius searches. This was fixed by adding coordinates and address metadata for the next-10 hospitals, plus a missing Cedars-Sinai address fallback.

## Scan-level comparison

First group:

```text
hospitals=7
local_jobs=273
matched_jobs=247
job_match_rate=90.5%
search_ready_rows=16501
rows_per_hospital_avg=2357.3
procedures_per_hospital_avg=24.1
formats=json 117 jobs / csv 156 jobs
```

Next-10 group:

```text
hospitals=10
local_jobs=390
matched_jobs=328
job_match_rate=84.1%
search_ready_rows=9269
rows_per_hospital_avg=926.9
procedures_per_hospital_avg=22.6
formats=json 195 jobs / csv 195 jobs
```

Interpretation:

- The new group has a slightly lower job match rate and fewer rows per hospital.
- The procedure coverage per hospital is close to the first group.
- Lower row density is expected because systems differ in how many payer/plan rows and cash/negotiated rows they publish.

## Combined output comparison

First group:

```text
combined_rows=16226
hospitals_with_rows=7
procedures=36
price_types=negotiated 15790 / cash 429 / median_allowed 7
data_quality_flags=ok 12925 / low_outlier 3301
missing_required=source_url 25
amount_min=1.00
amount_p50=691.66
amount_p95=28330.45
amount_max=499958.16
```

Next-10 group:

```text
combined_rows=5897
hospitals_with_rows=10
procedures=26
price_types=negotiated 4574 / cash 1322 / median_allowed 1
data_quality_flags=ok 4457 / low_outlier 1436 / high_outlier 4
missing_required=none
amount_min=0.01
amount_p50=555.61
amount_p95=20438.00
amount_max=943811.60
```

Interpretation:

- Required output fields are present and consistent for both groups.
- New group has **zero missing required source URLs**, which is better than the first group.
- New group has more cash rows proportionally, which is useful for the product.
- Outlier flags are active and consistent. The new group has 4 high outliers from UCI, which are excluded by existing relevance filtering.
- Very low values and very high values exist in both groups; relevance/outlier filtering is still necessary and working.

## Raw MRF format checks

The next-10 raw files begin with expected CMS-style fields such as:

- `hospital_name`
- `last_updated_on`
- `version`
- `location_name` / `hospital_location`
- `hospital_address`

Encoding/format notes:

- JSON files parse as JSON object files and expose standard top-level metadata.
- CSV files generally parse as `utf-8-sig`.
- Community Memorial Healthcare - Ventura requires `cp1252` fallback; this was already fixed in `run_layer4_local_scan_batch.py`.

## Frontend/API consistency check

Before the metadata fix, the new rows existed in SQLite but some hospitals could be skipped by radius search because `scripts/frontend_search.py` lacked coordinates/address fallbacks for several new hospitals.

Fixed by adding frontend metadata for:

- Hollywood Presbyterian Medical Center
- Huntington Hospital
- UCI Medical Center
- Hoag Hospital Newport Beach
- MemorialCare Orange Coast Medical Center
- Loma Linda University Medical Center
- Riverside Community Hospital
- Tri-City Medical Center
- Los Robles Regional Medical Center
- Community Memorial Healthcare - Ventura
- Cedars-Sinai Medical Center address fallback

Verification API smoke after fix:

```text
CT scan abdomen near Los Angeles, CA, 100 miles -> results 14
Community Memorial Healthcare - Ventura -> address shown
UCI Medical Center -> address shown
Cedars-Sinai Medical Center -> address shown
Los Robles Regional Medical Center -> address shown
```

## Test result

```text
80 passed in 2.76s
```

## Supporting outputs

- `data/research/mrf_group_quality_comparison_summary.json`
- `data/research/mrf_group_quality_comparison_by_hospital.csv`
- `data/research/next_10_hospital_contribution_summary.csv`

## Recommendation

Proceed with more data expansion. The next-10 batch is consistent enough to keep using this workflow.

For the next batch, add frontend location metadata at the same time as local source mappings so newly indexed hospitals are immediately visible in radius-based PC searches.
