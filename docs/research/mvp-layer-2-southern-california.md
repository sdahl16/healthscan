# MVP Layer 2 - Southern California 10-Procedure Validation

Status: passed

## Gate

Layer 2 passes when 8 of the 10 starter procedures return results from more than 3 Southern California hospitals each.

## Starter Procedures

The starter list is `data/reference/procedure_mapping.csv`.

## Data Quality

Outlier flags are now applied to indexed prices:

- `ok`
- `low_outlier`
- `high_outlier`
- `placeholder_amount`

For inpatient DRG procedures, amounts below $1,000 are marked `low_outlier`. This catches UCSD's $1.93 DRG 470 row without discarding the rest of the valid UCSD rows.

## Initial Coverage Test

The first Layer 2 coverage scan runs against local raw artifacts already created during Layer 1:

- UCLA full JSON MRF
- Scripps bounded CSV sample
- Keck DRG 470 CSV sample
- Sharp DRG 470 CSV sample
- UCSD DRG 470 JSON sample

Output: `data/research/mvp_layer2_initial_coverage.csv`

This is a starting point, not the final Layer 2 gate test. Most local samples were intentionally DRG 470-specific, so additional procedure-specific range extraction will be needed.

## Initial Results

Initial output files:

- `data/research/mvp_layer2_initial_coverage.csv`
- `data/research/mvp_layer2_gate_summary.csv`

| Procedure | Code | Hospitals With Results | Result |
| --- | --- | ---: | --- |
| Hip replacement | DRG 470 | 5 | pass |
| Knee replacement | DRG 470 | 5 | pass |
| Colonoscopy | CPT 45378 | 1 | fail |
| Vaginal delivery | DRG 807 | 1 | fail |
| C-section | DRG 783 | 1 | fail |
| Appendectomy | DRG 341 | 0 | fail |
| Cardiac catheterization | DRG 287 | 2 | fail |
| Brain MRI | CPT 70551 | 1 | fail |
| CT abdomen and pelvis | CPT 74176 | 1 | fail |
| Emergency department visit | CPT 99285 | 0 | fail |

Final gate status after primary, alternate, Providence, UCSD, and Rady scans: 10 of 10 procedures pass. Layer 2 requires 8 of 10.

## Next Testing Step

Run procedure-specific scans across the large SoCal MRFs instead of relying on DRG 470 samples. The next scanner should search for:

- DRG 807 and 783 in adult hospitals with obstetrics services.
- CPT 45378, 70551, 74176, and 99285 in outpatient rows.
- Alternate mappings for procedures currently missing, especially appendectomy and emergency department visits.

Alternate-code candidates are tracked in `data/reference/procedure_alternate_codes.csv`.

## Expanded Scan Results

Additional scan outputs:

- `data/research/mvp_layer2_csv_offsets.csv`
- `data/research/mvp_layer2_ucsd_offsets.csv`
- `data/research/mvp_layer2_providence_offsets.csv`
- `data/research/mvp_layer2_alternate_offsets.csv`
- `data/research/mvp_layer2_providence_alternate_offsets.csv`
- `data/research/mvp_layer2_rady_offsets.csv`

| Procedure | Hospitals With Results | Result |
| --- | ---: | --- |
| Hip replacement | 5 | pass |
| Knee replacement | 5 | pass |
| Colonoscopy | 5 | pass |
| Vaginal delivery | 4 | pass |
| C-section | 4 | pass |
| Appendectomy | 5 | pass |
| Cardiac catheterization | 5 | pass |
| Brain MRI | 4 | pass |
| CT abdomen and pelvis | 4 | pass |
| Emergency department visit | 4 | pass |

Rady Children's Hospital provided the final coverage source for Brain MRI, CT abdomen/pelvis, emergency department visit, and colonoscopy. Its CSV uses `HCPCS` as the code type for CPT-style rows such as 70551, 74176, 99285, and 45378, so the shared matcher now treats `HCPCS` as compatible when searching CPT codes.

Layer 2 gate result: pass, 10 of 10 starter procedures return results from more than 3 Southern California hospitals.
