# Indexed Price Coverage Summary

Generated: 2026-06-15

Source database: `data/processed/healthscan.sqlite`  
Table queried: `indexed_prices`

Note: the request described 30 procedure codes, but the supplied list contains 27 codes: 20 CPT, 1 HCPCS, and 6 DRG. This report covers exactly the provided codes.

| Plain procedure name | Code | Code type | Row count | Distinct hospitals | Price types present | Data quality flags |
| --- | --- | --- | ---: | ---: | --- | --- |
| Breast lumpectomy | 19301 | CPT | 635 | 6 | negotiated | low_outlier=18; ok=617 |
| Mastectomy | 19303 | CPT | 511 | 6 | negotiated | low_outlier=18; ok=493 |
| Tonsillectomy (child) | 42825 | CPT | 76 | 4 | negotiated | ok=76 |
| Tonsillectomy | 42826 | CPT | 400 | 6 | negotiated | low_outlier=18; ok=382 |
| Upper endoscopy with biopsy | 43235 | CPT | 649 | 7 | cash, negotiated | low_outlier=19; ok=630 |
| Upper endoscopy | 43239 | CPT | 561 | 7 | cash, negotiated | low_outlier=22; ok=539 |
| Appendectomy | 44970 | CPT | 1 | 1 | cash | ok=1 |
| Colonoscopy | 45378 | CPT | 4 | 4 | cash, negotiated | ok=4 |
| Gallbladder removal | 47562 | CPT | 376 | 6 | negotiated | ok=376 |
| Gallbladder removal (open) | 47563 | CPT | 373 | 6 | negotiated | ok=373 |
| Knee arthroscopy | 29881 | CPT | 0 | 0 | - | - |
| Shoulder arthroscopy | 29827 | CPT | 0 | 0 | - | - |
| Carpal tunnel surgery | 64721 | CPT | 0 | 0 | - | - |
| Cataract surgery | 66984 | CPT | 374 | 6 | cash, negotiated | ok=374 |
| MRI brain | 70551 | CPT | 4 | 4 | cash, negotiated | ok=4 |
| MRI spine | 72148 | CPT | 0 | 0 | - | - |
| CT scan abdomen | 74178 | CPT | 0 | 0 | - | - |
| Mammogram | 77067 | CPT | 852 | 7 | cash, negotiated | low_outlier=39; ok=813 |
| Echocardiogram | 93306 | CPT | 548 | 7 | cash, negotiated | low_outlier=5; ok=543 |
| Sleep study | 95810 | CPT | 227 | 6 | cash, negotiated | low_outlier=2; ok=225 |
| Screening colonoscopy | G0121 | HCPCS | 1 | 1 | negotiated | ok=1 |
| Cardiac catheterization | 287 | DRG | 4 | 4 | cash, negotiated | ok=4 |
| Appendectomy (inpatient) | 341 | DRG | 4 | 4 | negotiated | ok=4 |
| Knee replacement | 470 | DRG | 10 | 5 | negotiated | ok=10 |
| C-section | 783 | DRG | 3 | 3 | negotiated | ok=3 |
| Vaginal delivery | 807 | DRG | 3 | 3 | cash, negotiated | ok=3 |
| Coronary bypass (CABG) | 231 | DRG | 0 | 0 | - | - |

Overall coverage health: the current SQLite index is solid for the established MVP set: most common outpatient CPTs have 4-7 hospital coverage, inpatient DRGs 287, 341, 470, 783, and 807 have 3-5 hospitals, and the main price types available are negotiated and cash. Thin areas are the single-row codes, especially CPT 44970 and HCPCS G0121, which should be treated as best-effort. The known missing gaps are CPT 29881, 29827, 64721, 72148, 74178, and DRG 231; these should not be treated as available in the frontend until committed from a validated scan. For frontend reliability, rows with multi-hospital coverage and `ok` quality flags are suitable for normal display, while low-outlier rows should remain filtered or clearly suppressed and zero-row/single-hospital codes should be marked unavailable or limited coverage.
