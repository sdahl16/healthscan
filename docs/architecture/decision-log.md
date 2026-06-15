# Architecture Decision Log

Use this log only after the research gates provide evidence.

## ADR-001 - Data Acquisition Strategy

Status: proposed

Decision needed after Phases 1-4:

- Option A: direct MRF fetching via hospital `cms-hpt.txt`
- Option B: aggregator-first through a normalized pricing API
- Option C: hybrid coverage

### Proposed Direction

Use direct MRF discovery plus a background indexing job. The public query path must not fetch or parse hospital MRFs on demand.

The crawler should run on a schedule, fetch each hospital MRF out of band, stream the file, retain only rows matching the approved procedure/code list, and store normalized records in HealthScan's own database. A large source file, such as Mayo Clinic's 14.6 GB Rochester MRF, should become a small set of indexed rows for the procedures HealthScan supports.

### Why Not Query-Time Fetching

- MRFs can be gigabytes in size.
- Hospital-hosted links may be slow, blocked, redirected, zipped, extensionless, or served from third-party storage.
- Users should not wait on external hospital files during search.
- Query-time fetching creates unpredictable costs and failure modes.
- Procedure scope is intentionally narrow at MVP, so most MRF rows are irrelevant.

### Background Indexing Requirements

- Use `data/reference/procedure_mapping.csv` as the initial allowlist of codes.
- Stream CSV/JSON/ZIP inputs where possible instead of loading full files into memory.
- Normalize matched rows into a durable table keyed by hospital, code type, code, payer, plan, price field, source URL, and MRF date.
- Track source metadata separately: discovered URL, content type, size, checksum if available, crawl timestamp, parse status, and error details.
- Make indexing idempotent so a hospital can be re-crawled safely.
- Store rejected/unknown schema details for research without keeping full raw MRFs by default.
- Keep the user-facing search path database-only.

### Evidence Required

- Phase 1 `cms-hpt.txt` discovery pass/fail
- Phase 2 city sampling coverage and price population rates
- Procedure-code mapping reliability from Phase 3
- Aggregator availability, pricing, and coverage from Phase 4 if needed
- Indexing feasibility for large files using a stream-and-filter prototype

### Decision

Pending final Phase 2/3 evidence, but background indexing is now the default architecture constraint for any public-facing MVP.
