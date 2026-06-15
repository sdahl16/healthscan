from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from healthscan.claude_fallback import ClaudeFallbackError, ClaudeProcedureFallback, FallbackLogger, read_secret


QUERIES = (
    "laparoscopic cholecystectomy",
    "percutaneous coronary intervention",
    "transurethral resection of the prostate",
    "endoscopic retrograde cholangiopancreatography",
    "anterior cervical discectomy and fusion",
    "rotator cuff repair",
    "vitrectomy",
    "thyroidectomy",
    "laminectomy",
    "orchiectomy",
    "bronchoscopy with biopsy",
    "cardiac ablation",
    "spinal fusion",
    "knee meniscectomy",
    "prostatectomy",
)


def main() -> int:
    try:
        api_key = read_secret()
    except ClaudeFallbackError as error:
        print(str(error))
        return 2

    fallback = ClaudeProcedureFallback(
        api_key=api_key,
        logger=FallbackLogger(ROOT / "data" / "research" / "translation_fallback_log.csv"),
    )
    failures = 0
    for query in QUERIES:
        response = fallback.translate(query)
        invalid_types = [
            candidate.code_type
            for candidate in response.candidates
            if candidate.code_type not in {"CPT", "DRG", "HCPCS"}
        ]
        passed = bool(response.candidates) and not invalid_types
        failures += int(not passed)
        print(
            json.dumps(
                {
                    "query": query,
                    "candidate_count": len(response.candidates),
                    "invalid_code_types": invalid_types,
                    "passed": passed,
                }
            )
        )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
