# MVP Layer 3 - Search Normalization Validation

Status: passed

## Gate

Layer 3 passes when at least 8 of the 10 starter procedures produce search-ready normalized price rows from 3 or more Southern California hospitals.

A search-ready row must include:

- hospital name
- procedure name
- code type and code
- description when present
- setting when present
- display price and display price type
- gross, cash, negotiated, min, and max price fields when available
- payer and plan when available
- data quality flag
- source URL or evidence file

## Outputs

- Search export: `data/processed/layer3_search_results.csv`
- Gate summary: `data/research/mvp_layer3_gate_summary.csv`
- Export runner: `scripts/run_layer3_search_export.py`

## Result

Layer 3 result: passed. The export produced 42 search-ready rows. Ten of ten starter procedures have search-ready prices from at least 3 hospitals.

| Procedure | Search-Ready Hospitals | Result |
| --- | ---: | --- |
| Appendectomy | 5 | pass |
| Brain MRI | 4 | pass |
| C-section | 3 | pass |
| CT abdomen and pelvis | 4 | pass |
| Cardiac catheterization | 4 | pass |
| Colonoscopy | 5 | pass |
| Emergency department visit | 4 | pass |
| Hip replacement | 5 | pass |
| Knee replacement | 5 | pass |
| Vaginal delivery | 3 | pass |

## Notes

Knee replacement is materialized from the same DRG 470 source evidence used for hip replacement because the starter MVP mapping uses DRG 470 for both major hip and knee replacement without MCC. This is acceptable for the gate, but the product should eventually distinguish CPT 27447 when outpatient/surgeon-specific comparisons matter.

Rady Children's Hospital uses `HCPCS` as the code type for CPT-style rows such as 45378, 70551, 74176, and 99285. The normalizer treats those as compatible when the code itself matches the CPT search target.

UCSD JSON-fragment extraction added the third search-ready hospital for C-section and vaginal delivery. Those rows come from byte-offset evidence rather than a full MRF parse, so the next hardening task is still to move UCSD-style JSON fragments into a proper streaming JSON parser.
