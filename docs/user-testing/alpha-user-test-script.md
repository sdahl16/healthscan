# HealthScan Alpha User Test Script

Use this for quick non-mobile user tests. Aim for 5–10 minutes per tester.

## Setup

- Test URL: `http://127.0.0.1:4173/?v=user-test`
- Ask tester to think aloud.
- Do not explain the UI unless they get completely stuck.
- Record procedure, location, browser, and any confusing words.

## Tasks

1. **First impression**
   - Ask: “What do you think this tool does?”
   - Note whether they understand this is hospital-published price data, not an insurance estimate.

2. **Successful search**
   - Procedure: `Cataract surgery`
   - Location: `Los Angeles, CA 90095`
   - Ask them to identify the lowest displayed hospital price.

3. **Source/date trust check**
   - Ask them to find where the source/date information is shown.
   - Ask: “Would you trust this result enough to call the hospital or insurer? Why or why not?”

4. **Price-details interpretation**
   - Ask them to open **Price details**.
   - Ask them what `same amount ×N` means.
   - Ask what payer/plan wording means to them.

5. **Different market search**
   - Procedure: `MRI spine`
   - Location: `Chula Vista, CA 91911`
   - Ask whether the result list feels understandable and comparable.

6. **Empty/edge state**
   - Try a procedure/location combination that returns no nearby results or unsupported coverage.
   - Ask whether the page explains what happened and what to try next.

## Feedback questions

- What was clearest?
- What was confusing?
- Did the source/date information make the results more trustworthy?
- Did any medical/price language feel misleading?
- What would stop you from using this before scheduling care?
- What one thing should be improved before sharing with more people?

## Pass/fail checklist

- [ ] Tester understands prices are hospital-published standard charges, not final personal cost.
- [ ] Tester can complete a search without assistance.
- [ ] Tester can find a source/date for at least one result.
- [ ] Tester understands repeated displayed prices are grouped/summarized.
- [ ] Tester understands empty-state next steps.
- [ ] Tester notices the feedback path.
