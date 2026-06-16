# HealthScan Alpha External Site Review

Generated: 2026-06-16
Test target: `http://127.0.0.1:4173/`
Perspective: first-time external visitor using the local alpha site.

## Executive summary

The alpha is functional and surprisingly clear for a local prototype. Core flows work: procedure/location search, limited-coverage filtering, ambiguous-query clarification, unavailable-procedure handling, out-of-area handling, and price-details disclosure. No browser console JavaScript errors were observed during navigation and interactions.

The main risk is not broken functionality; it is trust and interpretation. A visitor can see prices, but the UI still needs stronger provenance, clearer price-type semantics, and more patient-facing explanation before it feels safe enough for medical/financial decision support.

## Tested flows

- Landing page load.
- Required field behavior via empty search click.
- Valid search: `colonoscopy` near `San Diego, CA`.
- Price filter: `Cash only`.
- Price details disclosure.
- Ambiguous query: `heart surgery`, then selected `Cardiac catheterization`.
- Invalid query: `pizza`.
- Indexed-but-unavailable query: `CABG` / DRG 231.
- Out-of-area query: `colonoscopy` near `San Francisco, CA`, then `Expand to 100 miles`.
- API smoke checks for search statuses.

## API smoke results

- `colonoscopy`, San Diego, all prices: `results`, 4 hospitals.
- `colonoscopy`, San Diego, cash: `limited_coverage`, 1 hospital.
- `heart surgery`: `clarification`, 2 options.
- `pizza`: `unavailable`, friendly unsupported-procedure message.
- `CABG`: `unavailable`, no indexed rows yet.
- `colonoscopy`, San Francisco: `no_results_near_location`.

## Findings

### 1. Price provenance is not visible enough

Severity: High
Category: Trust / Content

Result cards show hospital name, price, price type, code, and update timestamp, but they do not show the source file, hospital-published MRF URL, source date, or a clear explanation of how the display price was selected from many possible payer/plan rows.

Why it matters: For a medical price site, a user needs to know where the number came from and why it is shown. Without provenance, the app may look like it is giving authoritative patient cost estimates.

Recommendation:

- Add a `Source` link in each expanded price detail.
- Add `Why this price?` copy explaining ranking/selection: negotiated vs cash, lowest available, filtered outliers, etc.
- Distinguish `hospital file updated`, `parsed/indexed at`, and `price effective date` if available.

### 2. “Cash price” detail can show payer/plan text

Severity: High
Category: Data semantics / Trust

For Scripps Green colonoscopy, the card labels `$749` as `Cash price`, but the expanded detail shows payer/plan text: `MEDICARE ADVANTAGE [442] / MEDICARE HMO/PPO SHGH`.

Why it matters: This looks contradictory to a user. A cash/self-pay price should not appear tied to a Medicare Advantage payer/plan unless there is a known source-file quirk being explained.

Recommendation:

- Audit mapping of `price_type` and payer fields.
- If payer text is present on a cash row because of source-file structure, label it as `Source payer/plan field` or suppress it for cash rows.
- Add tests for cash-row display semantics.

### 3. Update timestamp appears internal rather than user-meaningful

Severity: Medium
Category: Content / Trust

Cards show `Updated 2026-06-15 20:26:29`, which appears to be a local parse/index timestamp, not necessarily the hospital MRF update date.

Why it matters: Users may interpret this as the hospital’s latest price update. That can overstate freshness.

Recommendation:

- Rename to `Indexed` if it is an ingest timestamp.
- Prefer hospital `last_updated_on` when available.
- Show both only if useful: `Hospital file date` and `Indexed by HealthScan`.

### 4. Address unavailable while distance is shown

Severity: Medium
Category: UX / Trust

Rady Children’s Hospital displays `Address unavailable` and `5.7 miles away` simultaneously.

Why it matters: Distance implies a known geocoded location. Seeing no address undermines confidence.

Recommendation:

- Add the address if known.
- If distance is calculated from a fallback coordinate, say so or hide distance until address metadata is complete.

### 5. Empty/unsupported states are functional but could be more helpful

Severity: Medium
Category: UX / Content

Unsupported and no-results states work, but they do not suggest specific supported procedures or nearby covered geographies except the 100-mile expansion button.

Recommendation:

- For unsupported queries, show 5–8 examples: colonoscopy, MRI brain, cataract surgery, hip replacement, etc.
- For unavailable indexed-code gaps like CABG, say `We recognize this procedure, but have not indexed DRG 231 yet` and optionally invite the user to try `cardiac catheterization` if relevant.
- For out-of-area searches, make the Southern California alpha limitation more prominent.

### 6. Frontend silently calls unavailable option endpoints

Severity: Low
Category: Technical / Maintainability

The frontend attempts `/api/procedures` and `/api/locations`; the current server only exposes `/api/health`, `/api/search`, and static files, so these likely fall back silently.

User impact is low because built-in fallback options populate the datalists. Developer/ops impact is mild confusion and avoidable network noise.

Recommendation:

- Either implement `/api/procedures` and `/api/locations`, or remove those fetches until the endpoints exist.

### 7. Alpha scope is not obvious enough at point of use

Severity: Low
Category: UX / Trust

The top eyebrow says Southern California launch coverage, and result copy says coverage is strongest there, but a user searching outside the area only learns after searching.

Recommendation:

- Add a short line under location input: `Alpha currently covers selected Southern California hospitals.`
- Consider a coverage map/list link.

## Positive observations

- Clean visual hierarchy: title, search form, controls, summary, disclaimers, cards.
- Disclaimers are visible before the result cards, not buried in footer text.
- Ambiguous query flow works and prevents single-guessing for risky terms like `heart surgery`.
- Out-of-area flow works and offers a radius expansion.
- Price details are readable and accessible through native disclosure controls.
- No JavaScript console errors observed during tested flows.

## Recommended next sprint priorities

1. Fix price-type/payer display semantics, especially cash rows.
2. Add source/provenance links and clarify timestamp meaning.
3. Improve unsupported/no-results guidance with examples and alpha coverage copy.
4. Complete missing hospital metadata such as Rady address.
5. Add/disable the currently missing option endpoints.

## Overall external-readiness assessment

Good alpha prototype. It is ready for internal demos and limited trusted-user feedback. Before broader public sharing, tighten provenance and price semantics so visitors do not mistake standard-charge data for personalized cost estimates.
