# Procedure Translation Layer

Status: implemented baseline

## Purpose

The translation layer converts plain-language procedure searches into schema-compatible CMS engine query candidates. It is intentionally provider-agnostic: deterministic lookup runs first, and any external model fallback must return structured candidates instead of free text.

## Contract

Input:

- `query`: user-entered procedure text
- `care_setting`: optional `inpatient`, `outpatient`, or `unknown`

Output:

- `status`: `match`, `ambiguous`, `clarify`, or `not_found`
- `candidates`: ranked procedure candidates
- `codes`: one or more query-ready code objects
- `procedure_code`: exact field for joining to `indexed_prices.procedure_code`
- `code_type`: exact field for joining to `indexed_prices.code_type`
- `plain_label`: canonical display label
- `confidence`: candidate confidence
- `clarifying_question`: populated for ambiguous or low-confidence cases

## Fallback Interface

External model providers plug in by implementing `TranslationFallback.translate(...)`.

Fallback responses must return:

- `code`
- `code_type`
- `plain_label`
- `confidence`
- optional `care_setting`

Free-text fallback answers are rejected as `not_found`. Low-confidence fallback answers return `clarify` with a clarifying question.

## Current Baseline

Files:

- Translator: `src/healthscan/translation.py`
- CLI: `python -m healthscan.cli translate "knee surgery"`
- Validation set: `data/reference/translation_validation_set.csv`
- Validation runner: `scripts/run_translation_validation.py`
- Validation output: `data/research/translation_validation_results.csv`

Validation result:

- 50 total regression cases
- 30 exact mapping cases
- 10 synonym/layperson cases
- 5 ambiguous cases
- 5 invalid cases
- exact-match accuracy: 30/30, 100 percent
- lookup latency target: under 100ms

## Notes

Ambiguous inputs such as `stomach surgery` return multiple candidates with confidence values and a clarifying question. They do not silently choose a single code.

Inputs with both inpatient and outpatient interpretations return multiple code types when care setting is unknown. Passing `--care-setting inpatient` filters to DRG where available; passing `--care-setting outpatient` filters to CPT/HCPCS where available.
