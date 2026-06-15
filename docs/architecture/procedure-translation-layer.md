# Procedure Translation Layer

Status: lookup, clarification, and Claude fallback baseline implemented

## Purpose

The translation layer converts plain-language procedure searches into schema-compatible CMS engine query candidates. It is intentionally separate from hospitals, locations, and prices. Deterministic lookup runs first; Claude is available only as an explicit fallback for queries the lookup table cannot resolve.

## Contract

Input:

- `query`: user-entered procedure text
- `setting`: optional `inpatient`, `outpatient`, `either`, or `unknown`
- `care_setting`: backwards-compatible alias accepted by current Python callers

Output:

- `status`: `match`, `ambiguous`, `clarify`, or `not_found`
- `source`: `lookup`, `fallback`, or `clarification_needed`
- `candidates`: ranked procedure candidates
- `codes`: one or more query-ready code objects
- `procedure_code`: exact field for joining to `indexed_prices.procedure_code`
- `code_type`: `CPT`, `DRG`, or `HCPCS`
- `description`: canonical display label
- `setting`: `inpatient`, `outpatient`, `either`, or `unknown`
- `confidence`: candidate confidence
- `clarifying_question`: populated for ambiguous or low-confidence cases

Clarification responses also serialize frontend-ready options:

```json
{
  "source": "clarification_needed",
  "prompt": "Which procedure did you mean?",
  "options": [
    {
      "label": "Coronary bypass (CABG)",
      "procedure_code": "231",
      "code_type": "DRG",
      "setting": "inpatient"
    }
  ]
}
```

## Fallback Interface

External model providers plug in by implementing `TranslationFallback.translate(...)`.

Claude fallback lives in `src/healthscan/claude_fallback.py` and supports:

- JSON-only prompt construction
- markdown code-fence stripping
- one retry after invalid JSON
- a 5-second HTTP timeout
- `APC`, `MS-DRG`, and `MSDRG` rejection
- candidate cap of 3
- optional CSV logging to `data/research/translation_fallback_log.csv`

The Claude API key is read from `.secrets/claude_api_key.txt` for live smoke tests. The `.secrets/` directory is ignored by git.

## Current Files

- Translator: `src/healthscan/translation.py`
- Claude fallback: `src/healthscan/claude_fallback.py`
- CLI: `python -m healthscan.cli translate "knee surgery"`
- CLI with fallback: `python -m healthscan.cli translate "vitrectomy" --claude-fallback`
- Validation set: `data/reference/translation_validation_set.csv`
- Validation runner: `scripts/run_translation_validation.py`
- Claude smoke runner: `scripts/run_claude_fallback_smoke.py`
- Validation output: `data/research/translation_validation_results.csv`

## Validation Result

- Full test suite: 63+ tests, all passing at the time of this baseline
- Translation validation: 50 total regression cases
- Exact mapping cases: 30/30
- Lookup latency target: under 100ms

## Notes

Ambiguous inputs such as `heart surgery` return multiple candidates with a clarifying question and flat `options` list. They do not silently choose a single code.

Inputs with both inpatient and outpatient interpretations return multiple code types when setting is unknown. Passing `--setting inpatient` filters to DRG where available; passing `--setting outpatient` filters to CPT/HCPCS where available.
