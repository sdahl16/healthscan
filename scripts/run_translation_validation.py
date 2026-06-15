from __future__ import annotations

import csv
from pathlib import Path

from healthscan.translation import ProcedureTranslator


ROOT = Path(__file__).resolve().parents[1]
VALIDATION_PATH = ROOT / "data" / "reference" / "translation_validation_set.csv"
OUT_PATH = ROOT / "data" / "research" / "translation_validation_results.csv"


def primary_code(response) -> tuple[str | None, str | None, str | None]:
    if not response.candidates or not response.candidates[0].codes:
        return None, None, None
    candidate = response.candidates[0]
    code = candidate.codes[0]
    return candidate.plain_label, code.code_type, code.procedure_code


def main() -> int:
    translator = ProcedureTranslator()
    rows: list[dict[str, str]] = []
    failures = 0
    exact_total = 0
    exact_correct = 0
    lookup_latency_ok = True

    with VALIDATION_PATH.open(newline="", encoding="utf-8") as handle:
        for case in csv.DictReader(handle):
            response = translator.translate(case["input"])
            label, code_type, code = primary_code(response)
            status_ok = response.status == case["expected_status"]
            code_ok = True
            if case["expected_code"]:
                code_ok = (
                    label == case["expected_label"]
                    and code_type == case["expected_code_type"]
                    and code == case["expected_code"]
                )
            if case["case_type"] == "exact":
                exact_total += 1
                exact_correct += int(status_ok and code_ok)
            if response.elapsed_ms >= 100 and response.source == "lookup":
                lookup_latency_ok = False
            passed = status_ok and code_ok
            failures += int(not passed)
            rows.append(
                {
                    "case_type": case["case_type"],
                    "input": case["input"],
                    "expected_status": case["expected_status"],
                    "actual_status": response.status,
                    "expected_label": case["expected_label"],
                    "actual_label": label or "",
                    "expected_code_type": case["expected_code_type"],
                    "actual_code_type": code_type or "",
                    "expected_code": case["expected_code"],
                    "actual_code": code or "",
                    "candidate_count": str(len(response.candidates)),
                    "elapsed_ms": str(response.elapsed_ms),
                    "passed": str(passed).lower(),
                }
            )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    exact_accuracy = exact_correct / exact_total if exact_total else 0
    print(f"cases={len(rows)} failures={failures} output={OUT_PATH}")
    print(f"exact_accuracy={exact_accuracy:.3f} exact_correct={exact_correct}/{exact_total}")
    print(f"lookup_latency_under_100ms={lookup_latency_ok}")
    return 0 if failures == 0 and exact_accuracy >= 0.9 and lookup_latency_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
