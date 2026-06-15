from __future__ import annotations

import re
from pathlib import Path

from healthscan.indexer import record_matches
from healthscan.search_export import records_from_json_fragment


def _find_object_start(text: str, position: int) -> int | None:
    depth = 0
    for index in range(position, -1, -1):
        char = text[index]
        if char == "}":
            depth += 1
        elif char == "{":
            if depth == 0:
                return index
            depth -= 1
    return None


def _find_object_end(text: str, position: int) -> int | None:
    depth = 0
    in_string = False
    escaped = False
    for index in range(position, len(text)):
        char = text[index]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index + 1
    return None


def _find_charge_item_start(text: str, position: int) -> int | None:
    description_matches = list(re.finditer(r"\{\s*\"description\"\s*:", text[:position]))
    if description_matches:
        return description_matches[-1].start()
    return _find_object_start(text, position)


def object_fragments_for_code(
    path: Path,
    *,
    code_type: str,
    code: str,
    chunk_size: int = 2_000_000,
    overlap: int = 250_000,
    max_matches: int | None = None,
) -> list[str]:
    pattern = re.compile(rf'"code"\s*:\s*"{re.escape(code)}"|"{re.escape(code)}"\s*,\s*"type"\s*:', re.IGNORECASE)
    fragments: list[str] = []
    seen: set[str] = set()
    buffer = ""
    with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            buffer += chunk
            search_end = max(0, len(buffer) - overlap)
            for match in pattern.finditer(buffer[:search_end]):
                start = _find_charge_item_start(buffer, match.start())
                end = _find_object_end(buffer, start) if start is not None else None
                if start is None or end is None:
                    continue
                fragment = buffer[start:end]
                key = fragment[:500]
                if key in seen:
                    continue
                seen.add(key)
                if _fragment_matches(fragment, code_type=code_type, code=code):
                    fragments.append(fragment)
                    if max_matches is not None and len(fragments) >= max_matches:
                        return fragments
            buffer = buffer[-overlap:]
    for match in pattern.finditer(buffer):
        start = _find_charge_item_start(buffer, match.start())
        end = _find_object_end(buffer, start) if start is not None else None
        if start is None or end is None:
            continue
        fragment = buffer[start:end]
        key = fragment[:500]
        if key not in seen and _fragment_matches(fragment, code_type=code_type, code=code):
            fragments.append(fragment)
            if max_matches is not None and len(fragments) >= max_matches:
                break
    return fragments


def object_fragments_for_codes(
    path: Path,
    *,
    targets: list[tuple[str, str]],
    chunk_size: int = 2_000_000,
    overlap: int = 250_000,
    max_matches_per_target: int | None = None,
) -> dict[tuple[str, str], list[str]]:
    unique_targets = list(dict.fromkeys((code_type.upper(), code) for code_type, code in targets))
    fragments: dict[tuple[str, str], list[str]] = {target: [] for target in unique_targets}
    if not unique_targets:
        return fragments

    code_pattern = "|".join(re.escape(code) for _, code in unique_targets)
    pattern = re.compile(rf'"code"\s*:\s*"(?P<code>{code_pattern})"', re.IGNORECASE)
    seen: set[tuple[tuple[str, str], str]] = set()
    buffer = ""
    with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            buffer += chunk
            search_end = max(0, len(buffer) - overlap)
            _collect_fragments_for_targets(
                buffer,
                pattern,
                unique_targets,
                fragments,
                seen,
                search_end=search_end,
                max_matches_per_target=max_matches_per_target,
            )
            if max_matches_per_target is not None and all(
                len(items) >= max_matches_per_target for items in fragments.values()
            ):
                return fragments
            buffer = buffer[-overlap:]
    _collect_fragments_for_targets(
        buffer,
        pattern,
        unique_targets,
        fragments,
        seen,
        search_end=None,
        max_matches_per_target=max_matches_per_target,
    )
    return fragments


def _collect_fragments_for_targets(
    text: str,
    pattern: re.Pattern[str],
    targets: list[tuple[str, str]],
    fragments: dict[tuple[str, str], list[str]],
    seen: set[tuple[tuple[str, str], str]],
    *,
    search_end: int | None,
    max_matches_per_target: int | None,
) -> None:
    targets_by_code: dict[str, list[tuple[str, str]]] = {}
    for target in targets:
        targets_by_code.setdefault(target[1], []).append(target)
    for match in pattern.finditer(text, 0, search_end or len(text)):
        start = _find_charge_item_start(text, match.start())
        end = _find_object_end(text, start) if start is not None else None
        if start is None or end is None:
            continue
        fragment = text[start:end]
        for target in targets_by_code.get(match.group("code"), []):
            if max_matches_per_target is not None and len(fragments[target]) >= max_matches_per_target:
                continue
            if not _fragment_matches(fragment, code_type=target[0], code=target[1]):
                continue
            key = (target, fragment[:500])
            if key in seen:
                continue
            seen.add(key)
            fragments[target].append(fragment)


def _fragment_matches(fragment: str, *, code_type: str, code: str) -> bool:
    normalized = fragment.replace('""', '"')
    type_variants = {code_type}
    if code_type.upper() == "DRG":
        type_variants.update({"MS-DRG", "MSDRG"})
    if code_type.upper() == "CPT":
        type_variants.add("HCPCS")
    code_patterns = [
        {"code": code, "type": code_type},
        {"code": code, "code_type": code_type},
    ]
    return any(record_matches(pattern, code_type=code_type, code=code) for pattern in code_patterns) or (
        re.search(rf'"code"\s*:\s*"{re.escape(code)}"', normalized) is not None
        and any(re.search(rf'"type"\s*:\s*"{re.escape(type_variant)}"', normalized) for type_variant in type_variants)
    )


def records_from_large_json_file(
    path: Path,
    *,
    code_type: str,
    code: str,
    max_matches: int | None = None,
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for fragment in object_fragments_for_code(path, code_type=code_type, code=code, max_matches=max_matches):
        records.extend(records_from_json_fragment(fragment))
    return records


def records_from_large_json_file_for_codes(
    path: Path,
    *,
    targets: list[tuple[str, str]],
    max_matches_per_target: int | None = None,
) -> dict[tuple[str, str], list[dict[str, object]]]:
    records: dict[tuple[str, str], list[dict[str, object]]] = {}
    fragments = object_fragments_for_codes(path, targets=targets, max_matches_per_target=max_matches_per_target)
    for target, target_fragments in fragments.items():
        records[target] = []
        for fragment in target_fragments:
            records[target].extend(records_from_json_fragment(fragment))
    return records
