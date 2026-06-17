# Next 10 hospital MRF expansion

Date: 2026-06-17

## Scope

Added 10 additional local machine-readable file sources north/west and around Southern California, following the prior full-local-MRF process.

## Added hospitals

1. Hollywood Presbyterian Medical Center — Los Angeles — JSON
2. Huntington Hospital — Los Angeles — CSV
3. UCI Medical Center — Orange County — JSON
4. Hoag Hospital Newport Beach — Orange County — CSV
5. MemorialCare Orange Coast Medical Center — Orange County — JSON
6. Loma Linda University Medical Center — Inland Empire — CSV
7. Riverside Community Hospital — Inland Empire — JSON
8. Tri-City Medical Center — San Diego — CSV
9. Los Robles Regional Medical Center — Ventura County — JSON
10. Community Memorial Healthcare - Ventura — Ventura County — CSV

City of Hope was initially verified through cms-hpt.txt but direct download was blocked with HTTP 403 from the local pipeline environment, so it was not promoted in this batch. Hollywood Presbyterian was used as the replacement verified local MRF.

## Files updated

- `data/reference/healthscan_next_10_mrf_sources.json`
- `data/reference/manual_mrf_registry.csv`
- `data/reference/layer4_hospital_targets.csv`
- `data/research/layer4_scan_engine_audit.csv`
- `data/research/indexing_expansion_worklist.csv`
- `src/healthscan/local_sources.py`
- `scripts/run_layer4_local_scan_batch.py`
- `tests/test_local_sources.py`
- `tests/test_translation_expansion_report.py`

Raw MRF files were downloaded under `data/raw/mrf/` and remain intentionally untracked/ignored.

## Pipeline results

Expanded scan:

```text
local_jobs=663
matched_jobs=575
search_ready_rows=25770
```

Combined/migrated outputs:

```text
combined_rows=22126
inserted_rows=22126
hospitals=20
mrf_sources=45
```

Functionality gate:

```text
queries=30
queries_with_results=30
queries_with_3plus_hospitals=30
queries_needing_indexing=0
gate_result=pass
```

Breadth gap:

```text
queries_below_breadth_target=0
additional_hospital_matches_needed=0
```

Full tests:

```text
79 passed in 4.82s
```

## Per-hospital contribution

See `data/research/next_10_hospital_contribution_summary.csv` for exact counts.

Highlights:

- Huntington Hospital: 4,249 local search-ready rows; 1,835 combined rows; 25 procedures represented.
- Loma Linda University Medical Center: 3,103 local search-ready rows; 2,241 combined rows; 17 procedures represented.
- MemorialCare Orange Coast Medical Center: 607 combined rows; 26 procedures represented.
- UCI Medical Center, Hoag, Riverside, Los Robles, and Hollywood Presbyterian each contributed broad 26-procedure coverage.

## Implementation notes

- Community Memorial Ventura CSV is not UTF-8; it requires cp1252/latin-1 fallback. `run_layer4_local_scan_batch.py` now tries `utf-8-sig`, then `cp1252`, then `latin-1` for CSV files.
- The scan worklist was stale relative to the full 30-query functionality set. Six missing validation procedures were added to `data/research/indexing_expansion_worklist.csv`, closing the breadth gap.
- The translation expansion report test no longer assumes live data has unindexed primary lookup gaps; it uses synthetic gap input instead, making the test stable after coverage improvements.
