# Alpha Feedback Implementation Plan

Generated: 2026-06-16
Source review: `docs/reports/alpha-external-site-review.md`

## Goal

Turn the external alpha review into a safer, clearer user-facing iteration without changing the core HealthScan architecture. This pass focuses on trust, provenance, and patient-facing interpretation before adding more data.

## Phase 1 — Trust and provenance

Deliverables:

- Show source/provenance context in every result card detail section.
- Distinguish hospital file/source metadata from HealthScan indexing timestamps.
- Explain how HealthScan picks the displayed price.

Quality gate:

- API response includes source/index metadata needed by frontend.
- Frontend renders source and selection explanation without console errors.

## Phase 2 — Price semantics

Deliverables:

- Avoid contradictory `Cash price` rows that display payer/plan text as if it were a normal plan-specific negotiated rate.
- Relabel payer/plan in detail rows so users understand it is a source-file field.
- Add tests for cash-row payer/plan display contract.

Quality gate:

- Cash rows remain searchable.
- Detail UI makes raw payer/plan fields less misleading.

## Phase 3 — Empty-state guidance

Deliverables:

- Add suggested procedure examples for unsupported searches.
- Clarify recognized-but-unindexed procedures such as CABG.
- Make Southern California alpha coverage more visible near the location field and in no-results states.

Quality gate:

- Unsupported, unavailable, and out-of-area flows include helpful next steps.

## Phase 4 — Metadata cleanup

Deliverables:

- Fill known missing hospital metadata where the UI currently says `Address unavailable` while also showing distance.
- If address remains unknown, avoid overconfident distance copy.

Quality gate:

- Rady Children’s no longer displays contradictory address/distance messaging for tested flows.

## Phase 5 — Verification and handoff

Deliverables:

- Full Python tests pass.
- Local API smoke checks pass.
- Browser smoke confirms the updated messages render.
- Push to GitHub after validation.
