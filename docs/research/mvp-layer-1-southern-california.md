# MVP Layer 1 - Southern California DRG 470 Validation

Status: ready to start

## Scope Change

Move the MVP Layer 1 testing market from New York to Southern California, focused on Los Angeles and San Diego.

This does not replace the Phase 2 five-city research. Phase 2 remains useful as national discovery evidence. The MVP proof-of-concept market is now Southern California because it provides two dense nearby metros, several large academic systems, and enough hospital diversity to test price variation.

## Gate

MVP Layer 1 passes when 5 or more Southern California hospitals return plausible hip replacement prices for DRG 470.

## Initial Target Systems

Targets are tracked in `data/reference/mvp_layer1_targets.csv`.

| Market | Hospital System | City | Priority |
| --- | --- | --- | ---: |
| Southern California | Cedars-Sinai | Los Angeles, CA | 1 |
| Southern California | UCLA Health | Los Angeles, CA | 1 |
| Southern California | Keck Medicine of USC | Los Angeles, CA | 1 |
| Southern California | UC San Diego Health | San Diego, CA | 1 |
| Southern California | Scripps Health | San Diego, CA | 1 |
| Southern California | Sharp HealthCare | San Diego, CA | 1 |
| Southern California | Providence Southern California | Los Angeles, CA | 2 |
| Southern California | Kaiser Permanente Southern California | Los Angeles, CA | 2 |
| Southern California | Palomar Health | San Diego, CA | 2 |
| Southern California | Rady Children's Hospital | San Diego, CA | 3 |

## Validation Plan

1. Run discovery with all three tiers: `cms-hpt.txt`, source-page scraping, manual registry.
2. Select at least 5 adult acute-care hospitals with accessible MRFs.
3. Stream/filter each MRF for DRG 470.
4. Normalize price rows into `indexed_prices`.
5. Check plausibility:
   - DRG 470 rows exist.
   - At least one gross, cash, negotiated, min, or max price is populated.
   - Amounts are numeric and not obvious placeholders.
   - Facility and source URL are auditable.

## Notes

Rady Children's is intentionally lower priority for DRG 470 because hip replacement is primarily an adult procedure. Keep it as a parser/discovery target, but do not rely on it for the 5-hospital DRG 470 gate.

## Discovery Snapshot

Initial discovery evidence is stored in `data/research/mvp_layer1_discovery_log.csv`.

The first proof target is UCLA Health because its Ronald Reagan UCLA Medical Center JSON MRF is manageable for a local prototype and contains `MS-DRG`/`DRG`-style records.

## DRG 470 Indexing Progress

Results are stored in `data/research/mvp_layer1_drg470_results.csv`.

| Hospital | Method | Price Rows | Amount Range | Result |
| --- | --- | ---: | --- | --- |
| Ronald Reagan UCLA Medical Center | Full JSON MRF | 23 | $2,175 to $48,081.25 | pass |
| Scripps Green Hospital | 5 MB CSV range sample | 5 | $16,164.18 to $145,426.90 | pass |
| Keck Hospital of USC | CSV range sample | 222 | $23,726.69 to $85,344.18 | pass |
| Sharp Chula Vista Medical Center | CSV range sample | 5 | $42,900.34 to $144,445.58 | pass |
| Cedars-Sinai Medical Center | Full JSON required | pending | pending | pending |
| UC San Diego Medical Center | JSON range sample | 566 | $1.93 to $143,892.34 | pass with outlier |

Current gate status: passed. The local SQLite index is populated at `data/processed/healthscan.sqlite` with 5 Southern California hospitals and 821 DRG 470 price rows. UC San Diego includes a low outlier minimum amount of $1.93, but 555 UCSD rows are within the plausible $1,000-$500,000 band.

Next candidates for broadening validation: Cedars-Sinai, Providence Southern California, Palomar Health, or Kaiser Permanente. Cedars-Sinai is included as a large-file candidate, but its server ignored byte-range requests and returned the full ~884 MB JSON, so it needs a full-download/streaming JSON strategy rather than the bounded range approach.
