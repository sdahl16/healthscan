# Phase 1 - Schema & Format Research

Status: in progress

## Official Sources

- CMS technical implementation guide: https://github.com/CMSgov/hospital-price-transparency
- CSV and JSON documentation: https://github.com/CMSgov/hospital-price-transparency/tree/master/documentation
- CMS validator tools: https://cmsgov.github.io/hpt-tool/

## 2026 Schema Notes

CMS states that the GitHub repository contains the data dictionaries, CSV templates, and JSON schema for hospital price transparency MRFs. The repository lists allowable CMS template formats as CSV tall, CSV wide, and JSON.

The repository README says CY2026 OPPS/ASC Final Rule updates add and remove several required elements effective January 1, 2026, with enforcement beginning April 1, 2026.

### Fields Relevant to HealthScan

| Category | Fields to Track |
| --- | --- |
| Hospital identity | hospital name, locations, addresses, license details, type 2 organizational NPI |
| MRF metadata | MRF date, CMS template version, attestation statement, attester name |
| Item/service | description, setting, code type, code, modifiers |
| Consumer price | gross charge, discounted cash price |
| Negotiated price | payer name, plan name, negotiated dollar amount, negotiated percentage, algorithm |
| Data quality | de-identified min/max negotiated charge, median allowed amount, 10th/90th percentile allowed amount, count of allowed amounts |

## Format Questions To Resolve

- Which template versions are present in 2026 hospital files?
- Are the target fields named consistently between CSV tall, CSV wide, and JSON?
- How often do hospitals publish pre-2026 schema files after April 1, 2026?
- Do files expose one code per row or multiple coding objects per service?
- Which price field is most useful for uninsured users: discounted cash price, gross charge, or allowed-amount statistics?

## Initial Discovery Targets

Record live discovery results in `data/research/phase1_discovery_log.csv`.

| Hospital System | Domain | Expected Outcome | Result |
| --- | --- | --- | --- |
| Mayo Clinic | mayoclinic.org | `cms-hpt.txt` resolves and links to an MRF | pass via `https://www.mayoclinic.org/cms-hpt.txt` |
| Cleveland Clinic | clevelandclinic.org | `cms-hpt.txt` resolves and links to an MRF | pass via alternate host `https://my.clevelandclinic.org/cms-hpt.txt` |
| Johns Hopkins Medicine | hopkinsmedicine.org | `cms-hpt.txt` resolves and links to an MRF | blocked: Cloudflare 403 from this environment |
| NewYork-Presbyterian | nyp.org | extra replacement validation target | pass via `https://www.nyp.org/cms-hpt.txt` |

Detailed evidence is stored in `data/research/phase1_validation_instances.csv`.

## Specific Validation Instances

| System | `cms-hpt.txt` Result | MRF Probe Result | Architecture Notes |
| --- | --- | --- | --- |
| Mayo Clinic | HTTP 200, `text/plain` | HTTP 200, `application/vnd.ms-excel`, 14,563,085,729 bytes | Direct discovery works, but the Rochester file is too large for request-time download. |
| Cleveland Clinic | HTTP 200, `text/plain` on `my.clevelandclinic.org` | HTTP 200, `application/octet-stream`, 51,348,717 bytes | Discovery requires host fallback beyond the marketing domain. |
| NewYork-Presbyterian | HTTP 200, `text/plain` | HTTP 200, `application/zip`, 3,392,675 bytes | MRF URL is a JSON ZIP with query parameters, so format detection must inspect path and content type. |
| Johns Hopkins Medicine | HTTP 403, Cloudflare HTML | not reached | Treat as unresolved; needs browser/manual review or alternate source-page discovery. |

## Implementation Findings

- `cms-hpt.txt` URLs may contain `mrf-url:` key-value text rather than one URL per line.
- Hospital-system domains may redirect or fail while another official subdomain works.
- Some MRF links use query parameters or extensionless download endpoints.
- File sizes vary dramatically; prefetching, streaming, caching, and city/procedure indexing will be required before any interactive app layer.
- Query-time MRF fetching is not viable for a public product. Use scheduled background indexing that filters each MRF down to the supported procedure-code list and stores only normalized matched records.

## Phase 1 Gate

Proceed to Phase 2 only if three hospitals have accessible `cms-hpt.txt` files that point to downloadable MRFs. The initial Johns Hopkins target is blocked from this environment, but the extra NYP validation gives three concrete pass instances. Continue Phase 2 with discovery fallback requirements documented rather than assuming one canonical host per hospital.
