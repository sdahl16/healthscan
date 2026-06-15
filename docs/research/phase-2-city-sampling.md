# Phase 2 - Five City Sampling

Status: preliminary accessibility pass complete

Use this file as the research notebook for the five-city data-quality pass. Store accessibility observations in `data/research/phase2_accessibility_log.csv`; procedure-level row observations will move into `data/research/city_sampling_log.csv` after the background indexer can stream/filter MRFs.

## Target Cities

| City | Research Purpose |
| --- | --- |
| New York, NY | Large market with likely price variation |
| Houston, TX | Large uninsured population and different market dynamics |
| Minneapolis, MN | Integrated health-system market |
| Phoenix, AZ | Fast-growing market with large and regional systems |
| Asheville, NC | Mid-size regional coverage test |

## Per-Hospital Checklist

- Confirm `cms-hpt.txt` resolves.
- Capture final MRF URL.
- Document MRF format: CSV tall, CSV wide, JSON, or unknown.
- Document file size.
- Search for DRG 470, DRG 807, and CPT 45378.
- Record whether cash price, gross charge, negotiated rates, and allowed-amount statistics are populated.
- Note placeholders, missing descriptions, unusual code formatting, compression, or redirects.

## City Summary Template

| City | Hospitals Checked | Accessible MRF % | Cash Price Populated % | Negotiated Rate Present % | Format Breakdown | Notes |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| New York, NY | 3 | 66.7% | pending | pending | JSON ZIP, CSV, blocked | NYP and NYU pass; Mount Sinai 403 |
| Houston, TX | 3 | 66.7% | pending | pending | `.ashx` download, CSV, missing | Houston Methodist and Memorial Hermann pass; St. Luke's 404 |
| Minneapolis, MN | 3 | 100.0% | pending | pending | CSV, extensionless download | All three sampled systems pass |
| Phoenix, AZ | 3 | 33.3% | pending | pending | CSV, blocked/missing | HonorHealth passes; Banner 403; Dignity 404 |
| Asheville, NC | 3 | 100.0% | pending | pending | JSON Blob, wrapped download, extensionless download | All three sampled systems pass, but AdventHealth URL needs unwrapping |

## Phase 2 Gate

Direct MRF fetching remains viable if at least three of the five cities show more than 70 percent of hospitals with accessible, populated MRFs.

Preliminary accessibility-only result: 2 of 5 cities exceed 70%, so the strict city gate is not met yet. See `docs/research/phase-2-gate.md` for the decision record and required follow-up.
