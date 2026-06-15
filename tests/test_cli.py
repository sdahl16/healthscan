from __future__ import annotations

import json

from healthscan.cli import build_parser


def test_translate_cli_accepts_claude_fallback_options() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "translate",
            "rare procedure",
            "--setting",
            "outpatient",
            "--claude-fallback",
            "--claude-model",
            "claude-test",
            "--fallback-log",
            "",
        ]
    )

    assert args.query == "rare procedure"
    assert args.care_setting == "outpatient"
    assert args.claude_fallback is True
    assert args.claude_model == "claude-test"
    assert args.fallback_log == ""


def test_translate_cli_lookup_path_still_runs_without_fallback(capsys) -> None:
    parser = build_parser()
    args = parser.parse_args(["translate", "knee surgery"])

    exit_code = args.func(args)
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "match"
    assert payload["candidates"][0]["codes"][0]["procedure_code"] == "470"
