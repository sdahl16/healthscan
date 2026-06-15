from __future__ import annotations

import argparse
import json

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
    translator = ProcedureTranslator()
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
        choices=["inpatient", "outpatient", "unknown"],
        default="unknown",
        help="Optional care-setting hint for DRG vs CPT/HCPCS selection.",
    )
    translate_parser.set_defaults(func=_translate)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
