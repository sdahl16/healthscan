from __future__ import annotations

import csv
from pathlib import Path

from healthscan.claude_fallback import (
    ClaudeProcedureFallback,
    ClaudeFallbackError,
    FallbackLogger,
    parse_claude_procedure_json,
    read_secret,
    strip_json_code_fence,
)


ROOT = Path(__file__).resolve().parents[1]


def workspace_tmp_path(name: str) -> Path:
    path = ROOT / "data" / "tmp" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    return path


def message(text: str) -> dict:
    return {"content": [{"type": "text", "text": text}]}


def test_strip_json_code_fence_accepts_markdown_wrapped_array() -> None:
    assert strip_json_code_fence("```json\n[]\n```") == "[]"


def test_parse_claude_json_converts_valid_candidates() -> None:
    parsed = parse_claude_procedure_json(
        """
        [
          {
            "plain_name": "Thyroidectomy",
            "procedure_code": "60240",
            "code_type": "CPT",
            "setting": "outpatient",
            "confidence": "high",
            "reason": "Procedure match"
          }
        ]
        """
    )

    assert len(parsed.procedures) == 1
    procedure = parsed.procedures[0]
    assert procedure.code == "60240"
    assert procedure.code_type == "CPT"
    assert procedure.description == "Thyroidectomy"
    assert procedure.setting == "outpatient"
    assert procedure.confidence == 0.86


def test_parse_claude_json_rejects_apc_and_ms_drg_outputs() -> None:
    parsed = parse_claude_procedure_json(
        """
        [
          {"plain_name": "Unsupported APC", "procedure_code": "123", "code_type": "APC", "setting": "outpatient", "confidence": "high"},
          {"plain_name": "Unsupported DRG spelling", "procedure_code": "470", "code_type": "MS-DRG", "setting": "inpatient", "confidence": "high"},
          {"plain_name": "Colonoscopy", "procedure_code": "45378", "code_type": "CPT", "setting": "outpatient", "confidence": "high"}
        ]
        """
    )

    assert [procedure.description for procedure in parsed.procedures] == ["Colonoscopy"]


def test_claude_fallback_retries_once_after_invalid_json() -> None:
    calls = []

    def transport(payload: dict, timeout: float) -> dict:
        calls.append(payload)
        if len(calls) == 1:
            return message("not json")
        return message(
            '[{"plain_name":"Laminectomy","procedure_code":"63047","code_type":"CPT","setting":"outpatient","confidence":"high","reason":"match"}]'
        )

    fallback = ClaudeProcedureFallback(transport=transport)
    response = fallback.translate("laminectomy")

    assert len(calls) == 2
    assert len(response.candidates) == 1
    assert response.candidates[0].code == "63047"


def test_claude_fallback_empty_array_returns_graceful_no_match() -> None:
    fallback = ClaudeProcedureFallback(transport=lambda payload, timeout: message("[]"))
    response = fallback.translate("pizza")

    assert response.candidates == ()
    assert response.message is None


def test_claude_fallback_logs_outputs() -> None:
    log_path = workspace_tmp_path("fallback-log.csv")
    fallback = ClaudeProcedureFallback(
        logger=FallbackLogger(log_path),
        transport=lambda payload, timeout: message(
            '[{"plain_name":"Vitrectomy","procedure_code":"67036","code_type":"CPT","setting":"outpatient","confidence":"high","reason":"match"}]'
        ),
    )

    fallback.translate("vitrectomy")

    with log_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["query"] == "vitrectomy"
    assert rows[0]["status"] == "match"
    assert rows[0]["candidate_count"] == "1"


def test_placeholder_secret_is_not_accepted() -> None:
    secret_path = workspace_tmp_path("placeholder-claude-key.txt")
    secret_path.write_text("Paste your Claude API key here when you are ready.", encoding="utf-8")

    try:
        read_secret(secret_path)
    except ClaudeFallbackError as error:
        assert "not configured" in str(error)
    else:
        raise AssertionError("Placeholder Claude API key should not be accepted")
