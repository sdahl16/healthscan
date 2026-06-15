from __future__ import annotations

import csv
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from healthscan.translation import FallbackProcedure, FallbackResponse, normalize_code_type, parse_setting


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SECRET_PATH = ROOT / ".secrets" / "claude_api_key.txt"
DEFAULT_LOG_PATH = ROOT / "data" / "research" / "translation_fallback_log.csv"
DEFAULT_MODEL = "claude-haiku-4-5"
ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


PROMPT_TEMPLATE = """You are a medical billing code assistant. The user is searching for a hospital procedure to compare prices.

User input: "{query}"

Return a JSON array of the most likely procedure matches. Each object must have:
- plain_name: short plain-language label
- procedure_code: the CPT, HCPCS, or DRG code as a string, e.g. "45378", "G0121", "470"
- code_type: one of "CPT", "DRG", "HCPCS" only - do not use "APC" or "MS-DRG"
- setting: one of "inpatient", "outpatient", "either"
- confidence: one of "high", "low"
- reason: one sentence explaining the match

Rules:
- Prefer CPT codes for outpatient procedures - they have the best data coverage
- Use DRG for inpatient hospital stays
- Use HCPCS only for known HCPCS-coded procedures, e.g. screening colonoscopy G0121
- Never output APC or MS-DRG as code_type
- Return 1 result if the input is clearly one procedure
- Return 2-3 results if the input is ambiguous
- Return an empty array [] if the input is not a recognizable hospital procedure
- Return JSON only. No explanation, no markdown, no preamble.
"""


class ClaudeFallbackError(RuntimeError):
    pass


@dataclass(frozen=True)
class ParsedClaudeResult:
    procedures: tuple[FallbackProcedure, ...]
    raw_json: str


def read_secret(path: Path = DEFAULT_SECRET_PATH) -> str:
    value = path.read_text(encoding="utf-8").strip()
    if not value or value.startswith("Paste your Claude API key"):
        raise ClaudeFallbackError(f"Claude API key is not configured at {path}")
    return value


def build_prompt(query: str) -> str:
    return PROMPT_TEMPLATE.format(query=query.replace('"', '\\"'))


def strip_json_code_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]).strip()
    return stripped


def confidence_to_score(value: Any) -> float:
    if isinstance(value, (int, float)):
        return max(0.0, min(float(value), 1.0))
    normalized = str(value or "").strip().lower()
    if normalized == "high":
        return 0.86
    if normalized == "low":
        return 0.45
    return 0.0


def parse_claude_procedure_json(text: str) -> ParsedClaudeResult:
    raw_json = strip_json_code_fence(text)
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError as error:
        raise ClaudeFallbackError(f"Claude fallback returned invalid JSON: {error}") from error
    if not isinstance(payload, list):
        raise ClaudeFallbackError("Claude fallback JSON must be an array.")

    procedures: list[FallbackProcedure] = []
    for item in payload[:3]:
        if not isinstance(item, dict):
            continue
        raw_code_type = str(item.get("code_type") or "").strip()
        if raw_code_type.upper() in {"APC", "MS-DRG", "MSDRG"}:
            continue
        try:
            code_type = normalize_code_type(raw_code_type)
        except ValueError:
            continue
        code = str(item.get("procedure_code") or "").strip()
        description = str(item.get("plain_name") or "").strip()
        if not code or not description:
            continue
        procedures.append(
            FallbackProcedure(
                code=code,
                code_type=code_type,
                description=description,
                confidence=confidence_to_score(item.get("confidence")),
                setting=parse_setting(str(item.get("setting") or ""), code_type),
            )
        )
    return ParsedClaudeResult(procedures=tuple(procedures), raw_json=raw_json)


def extract_text_from_message(message: dict[str, Any]) -> str:
    parts = message.get("content")
    if not isinstance(parts, list):
        return ""
    return "\n".join(
        str(part.get("text") or "")
        for part in parts
        if isinstance(part, dict) and part.get("type") == "text"
    ).strip()


class FallbackLogger:
    def __init__(self, path: Path = DEFAULT_LOG_PATH) -> None:
        self.path = path

    def write(self, *, query: str, status: str, raw_output: str, candidate_count: int, elapsed_ms: float) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        exists = self.path.exists()
        with self.path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=("timestamp", "query", "status", "candidate_count", "elapsed_ms", "raw_output"),
            )
            if not exists:
                writer.writeheader()
            writer.writerow(
                {
                    "timestamp": str(round(time.time(), 3)),
                    "query": query,
                    "status": status,
                    "candidate_count": str(candidate_count),
                    "elapsed_ms": str(round(elapsed_ms, 3)),
                    "raw_output": raw_output,
                }
            )


class ClaudeProcedureFallback:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        api_key_path: Path = DEFAULT_SECRET_PATH,
        model: str = DEFAULT_MODEL,
        timeout_seconds: float = 5.0,
        max_tokens: int = 512,
        logger: FallbackLogger | None = None,
        transport: Callable[[dict[str, Any], float], dict[str, Any]] | None = None,
    ) -> None:
        self.api_key = api_key
        self.api_key_path = api_key_path
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_tokens = max_tokens
        self.logger = logger
        self.transport = transport

    def translate(self, query: str, *, care_setting: str = "unknown") -> FallbackResponse:
        started = time.perf_counter()
        prompt = build_prompt(query)
        raw_output = ""
        status = "not_found"
        try:
            raw_output = self._complete(prompt)
            parsed = parse_claude_procedure_json(raw_output)
        except ClaudeFallbackError as first_error:
            try:
                retry_prompt = (
                    f"{prompt}\n\nPrevious response could not be parsed as the required JSON array: {first_error}. "
                    "Return only a valid JSON array now."
                )
                raw_output = self._complete(retry_prompt)
                parsed = parse_claude_procedure_json(raw_output)
            except ClaudeFallbackError as second_error:
                self._log(query, "error", raw_output or str(second_error), 0, started)
                return FallbackResponse(message=str(second_error))
        except (TimeoutError, urllib.error.URLError) as error:
            self._log(query, "timeout", str(error), 0, started)
            return FallbackResponse(message="Claude fallback timed out. Try again in a moment.")

        if parsed.procedures:
            status = "match"
        self._log(query, status, parsed.raw_json, len(parsed.procedures), started)
        return FallbackResponse(candidates=parsed.procedures)

    def _complete(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        message = self.transport(payload, self.timeout_seconds) if self.transport else self._http_message(payload)
        text = extract_text_from_message(message)
        if not text:
            raise ClaudeFallbackError("Claude fallback response did not contain text output.")
        return text

    def _http_message(self, payload: dict[str, Any]) -> dict[str, Any]:
        api_key = self.api_key or read_secret(self.api_key_path)
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            ANTHROPIC_MESSAGES_URL,
            data=body,
            headers={
                "content-type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": ANTHROPIC_VERSION,
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))

    def _log(self, query: str, status: str, raw_output: str, candidate_count: int, started: float) -> None:
        if self.logger is None:
            return
        self.logger.write(
            query=query,
            status=status,
            raw_output=raw_output,
            candidate_count=candidate_count,
            elapsed_ms=(time.perf_counter() - started) * 1000,
        )
