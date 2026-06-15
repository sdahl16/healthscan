# Discovery Strategy

Root-domain `cms-hpt.txt` discovery works in theory, but Phase 2 showed too many real-world failure modes for it to be the only discovery mechanism. HealthScan should use a three-tier discovery layer.

## Tier 1 - `cms-hpt.txt`

Try `https://{domain}/cms-hpt.txt` and `https://www.{domain}/cms-hpt.txt`.

This is still the preferred source when it works because it is explicit, lightweight, and designed for machine discovery.

## Tier 2 - Source-Page Scraping

When `cms-hpt.txt` returns 403, 404, or has no usable `mrf-url`, try known price-transparency page paths and scrape links that match MRF patterns.

Candidate path examples:

- `/patients/billing/price-transparency`
- `/patients-visitors/billing-insurance/price-transparency`
- `/patient-resources/billing-insurance/price-transparency`
- `/patient-resources/patient-financial-resources/pricing-transparency`
- `/patients-visitors/paying-for-care/hospital-price-transparency`
- `/patients/billing-finance/comprehensive-hospital-charges`
- `/billing-insurance/price-transparency`
- `/price-transparency`
- `/standard-charges`

Known link patterns:

- `standardcharges`
- `standard-charges`
- `MRFDownload`
- `pricing_files`
- `.csv`, `.json`, `.zip`, `.gz`, `.ashx`

## Tier 3 - Manual Registry

For high-value hospitals where automated discovery consistently fails, maintain a curated registry in `data/reference/manual_mrf_registry.csv`.

This is intentionally pragmatic. Large systems such as Mount Sinai, Johns Hopkins, Banner, Dignity, and St. Luke's should not block market coverage simply because their discovery path is hostile to automation.

## Parser Test Matrix

The discovery and parser stack must handle:

| Pattern | Required Handling |
| --- | --- |
| Huge CSV | Stream rows and filter by supported procedure codes. |
| JSON ZIP | Download/open ZIP, stream JSON entries, classify schema. |
| `.ashx` download | Use headers/content sniffing, not file extension. |
| Extensionless endpoint | Follow redirects and inspect content type/signature. |
| Signed Blob URL | Preserve full query string and track expiry risk. |
| Wrapped URL | Decode or follow wrappers such as URLDefense. |
| 403/404 root domain | Fall back to source-page scraping and manual registry. |
