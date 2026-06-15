from __future__ import annotations

import argparse
import json
from pathlib import Path

from healthscan.claude_fallback import ClaudeProcedureFallback, FallbackLogger
from healthscan.discovery import discover_first_available, likely_mrf_links
from healthscan.translation import ProcedureTranslator, response_to_dict


def _discover(args: argparse.Namespace) -> int:
    result = discover_first_available(args.target, timeout=args.timeout)
    payload = {
        "source_url": result.source_url,
        "status_code": result.status_code,
        "content_type": result.content_type,
        "links": result.links,
        "likely_mrf_links": likely_mrf_links(result.links),
    }
    print(json.dumps(payload, indent=2))
    return 0


def _translate(args: argparse.Namespace) -> int:
    fallback = None
    if args.claude_fallback:
        fallback = ClaudeProcedureFallback(
            model=args.claude_model,
            logger=FallbackLogger(Path(args.fallback_log)) if args.fallback_log else None,
        )
    translator = ProcedureTranslator(fallback=fallback)
    response = translator.translate(args.query, care_setting=args.care_setting)
    print(json.dumps(response_to_dict(response), indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="healthscan")
    subparsers = parser.add_subparsers(dest="command", required=True)

    discover_parser = subparsers.add_parser("discover", help="Fetch and parse a hospital cms-hpt.txt file.")
    discover_parser.add_argument("target", help="Hospital domain or direct cms-hpt.txt URL.")
    discover_parser.add_argument("--timeout", type=int, default=20)
    discover_parser.set_defaults(func=_discover)

    translate_parser = subparsers.add_parser("translate", help="Resolve a plain-language procedure to billing codes.")
    translate_parser.add_argument("query", help="Plain-language procedure query.")
    translate_parser.add_argument(
        "--care-setting",
        "--setting",
        dest="care_setting",
        choices=["inpatient", "outpatient", "either", "unknown"],
        default="unknown",
        help="Optional care-setting hint for DRG vs CPT/HCPCS selection.",
    )
    translate_parser.add_argument(
        "--claude-fallback",
        action="store_true",
        help="Use Claude as a fallback when deterministic lookup cannot resolve the query.",
    )
    translate_parser.add_argument(
        "--claude-model",
        default="claude-haiku-4-5",
        help="Claude model ID to use when --claude-fallback is enabled.",
    )
    translate_parser.add_argument(
        "--fallback-log",
        default="data/research/translation_fallback_log.csv",
        help="CSV path for Claude fallback query logging. Use an empty string to disable.",
    )
    translate_parser.set_defaults(func=_translate)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
