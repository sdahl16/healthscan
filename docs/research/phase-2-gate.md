# Phase 2 Gate - Accessibility Validation

Status: passed after manual-registry fallback; continue with procedure-level indexing validation.

The first pass tested `cms-hpt.txt` accessibility and first MRF URL probeability for 15 hospitals across the five target cities. Evidence is stored in `data/research/phase2_accessibility_log.csv`.

After populating `data/reference/manual_mrf_registry.csv`, the failed systems were rerun through the fallback strategy. Fallback-aware evidence is stored in `data/research/phase2_accessibility_with_fallback_log.csv`.

## City Results

| City | Hospitals Checked | Accessible MRFs | Accessible % | Gate Result |
| --- | ---: | ---: | ---: | --- |
| New York, NY | 3 | 2 | 66.7% | fail |
| Houston, TX | 3 | 2 | 66.7% | fail |
| Minneapolis, MN | 3 | 3 | 100.0% | pass |
| Phoenix, AZ | 3 | 1 | 33.3% | fail |
| Asheville, NC | 3 | 3 | 100.0% | pass |

## Overall Gate Result

The original Phase 2 gate requires at least 3 of 5 cities to show more than 70% of hospitals with accessible, populated MRFs. This preliminary accessibility-only pass has 2 of 5 cities above 70%, so the strict gate is not met yet.

This does not invalidate direct MRF indexing. It means the crawler needs alternate discovery strategies before city rollout:

- Try known health-system subdomains, not just root and `www`.
- Follow source-page URLs when `mrf-url` is missing or blocked.
- Decode wrapped download URLs such as URLDefense links.
- Treat 403 responses as unresolved until checked with browser/manual discovery.
- Add more than 3 hospitals per city so one blocked health system does not decide an entire market.

## Fallback Rerun Result

| City | Hospitals Checked | Accessible MRFs With Fallback | Accessible % | Gate Result |
| --- | ---: | ---: | ---: | --- |
| New York, NY | 3 | 3 | 100.0% | pass |
| Houston, TX | 3 | 3 | 100.0% | pass |
| Minneapolis, MN | 3 | 3 | 100.0% | pass |
| Phoenix, AZ | 3 | 3 | 100.0% | pass |
| Asheville, NC | 3 | 3 | 100.0% | pass |

Fallback-aware Phase 2 accessibility result: 5 of 5 cities exceed 70%, so the accessibility gate passes.

Mount Sinai remains locally blocked by Akamai for this environment, but the registry entry was externally verified by the web-enabled research bot. Banner, Dignity, and St. Luke's registry MRF URLs probed successfully with HTTP 200 from this environment.

## Format Findings

| Format / Delivery Pattern | Examples |
| --- | --- |
| JSON ZIP | NewYork-Presbyterian |
| Large CSV | NYU Langone, M Health Fairview |
| `.ashx` download | Houston Methodist, Memorial Hermann |
| Extensionless download endpoint | Hennepin Healthcare, Pardee Hospital |
| Signed Blob URL | Mission Health |
| Wrapped third-party URL | AdventHealth |

## Next Validation Step

Build the background indexing prototype against one small/medium MRF and one large MRF. The next gate should verify whether the crawler can extract DRG 470, DRG 807, and CPT 45378 rows without downloading or storing full raw files in the query path.
