from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from healthscan.claude_fallback import ClaudeFallbackError, ClaudeProcedureFallback, FallbackLogger, read_secret
from healthscan.translation import ProcedureTranslator, response_to_dict


DEFAULT_QUERIES = (
    "transurethral resection of the prostate",
    "endoscopic retrograde cholangiopancreatography",
    "vitrectomy",
    "pizza",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a live Claude fallback smoke test without printing secrets.")
    parser.add_argument("queries", nargs="*", default=DEFAULT_QUERIES)
    parser.add_argument("--model", default="claude-haiku-4-5")
    parser.add_argument("--secret-path", default=str(ROOT / ".secrets" / "claude_api_key.txt"))
    parser.add_argument("--log-path", default=str(ROOT / "data" / "research" / "translation_fallback_log.csv"))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    secret_path = Path(args.secret_path)
    try:
        api_key = read_secret(secret_path)
    except ClaudeFallbackError as error:
        print(str(error))
        return 2

    fallback = ClaudeProcedureFallback(
        api_key=api_key,
        model=args.model,
        logger=FallbackLogger(Path(args.log_path)),
    )
    translator = ProcedureTranslator(fallback=fallback)
    failures = 0
    for query in args.queries:
        response = translator.translate(query)
        payload = response_to_dict(response)
        if response.source == "fallback" and response.status in {"match", "not_found", "clarify"}:
            status = "ok"
        else:
            status = "unexpected"
            failures += 1
        print(
            json.dumps(
                {
                    "query": query,
                    "smoke_status": status,
                    "translation_status": payload["status"],
                    "source": payload["source"],
                    "candidate_count": len(payload["candidates"]),
                }
            )
        )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
