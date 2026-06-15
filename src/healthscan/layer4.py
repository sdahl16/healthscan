from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TARGETS_PATH = ROOT / "data" / "reference" / "layer4_hospital_targets.csv"
DEFAULT_MANUAL_REGISTRY_PATH = ROOT / "data" / "reference" / "manual_mrf_registry.csv"
DEFAULT_SEARCH_RESULTS_PATH = ROOT / "data" / "processed" / "layer3_search_results.csv"


@dataclass(frozen=True)
class Layer4Target:
    hospital_name: str
    hospital_system: str
    domain: str
    region: str
    priority: int
    notes: str


@dataclass(frozen=True)
class KnownSource:
    source_url: str
    mrf_url: str
    status: str
    notes: str


@dataclass(frozen=True)
class HospitalCoverage:
    hospital_name: str
    hospital_system: str
    region: str
    priority: int
    domain: str
    source_status: str
    mrf_url: str | None
    current_search_ready_rows: int
    current_search_ready_procedures: int
    engine_status: str
    next_action: str
    notes: str


def normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def load_targets(path: Path = DEFAULT_TARGETS_PATH) -> list[Layer4Target]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [
            Layer4Target(
                hospital_name=row["hospital_name"],
                hospital_system=row["hospital_system"],
                domain=row["domain"],
                region=row["region"],
                priority=int(row["priority"]),
                notes=row["notes"],
            )
            for row in csv.DictReader(handle)
        ]


def load_known_sources(path: Path = DEFAULT_MANUAL_REGISTRY_PATH) -> dict[str, KnownSource]:
    sources: dict[str, KnownSource] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            source = KnownSource(
                source_url=row["source_url"],
                mrf_url=row["mrf_url"],
                status=row["status"],
                notes=row["notes"],
            )
            for key in (row["hospital_system"], row["domain"]):
                if key:
                    sources[normalize_name(key)] = source
    return sources


def load_search_ready_counts(path: Path = DEFAULT_SEARCH_RESULTS_PATH) -> dict[str, tuple[int, int, str | None]]:
    counts: dict[str, tuple[int, int, str | None]] = {}
    if not path.exists():
        return counts
    procedure_sets: dict[str, set[str]] = {}
    row_counts: dict[str, int] = {}
    source_urls: dict[str, str] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            key = normalize_name(row["hospital"])
            row_counts[key] = row_counts.get(key, 0) + 1
            procedure_sets.setdefault(key, set()).add(row["procedure_name"])
            if row.get("source_url"):
                source_urls.setdefault(key, row["source_url"])
    for key, rows in row_counts.items():
        counts[key] = (rows, len(procedure_sets.get(key, set())), source_urls.get(key))
    return counts


def source_for_target(target: Layer4Target, sources: dict[str, KnownSource]) -> KnownSource | None:
    for key in (target.hospital_name, target.hospital_system, target.domain):
        source = sources.get(normalize_name(key))
        if source:
            return source
    return None


def coverage_for_targets(
    targets: list[Layer4Target],
    *,
    sources: dict[str, KnownSource],
    search_counts: dict[str, tuple[int, int, str | None]],
) -> list[HospitalCoverage]:
    coverage: list[HospitalCoverage] = []
    for target in targets:
        known_source = source_for_target(target, sources)
        rows, procedures, indexed_source_url = search_counts.get(normalize_name(target.hospital_name), (0, 0, None))
        if rows > 0:
            engine_status = "search_ready"
            next_action = "include_in_expanded_regression"
        elif known_source:
            engine_status = "source_known_needs_indexing"
            next_action = "run_streaming_parser"
        else:
            engine_status = "needs_discovery"
            next_action = "discover_source_url"

        coverage.append(
            HospitalCoverage(
                hospital_name=target.hospital_name,
                hospital_system=target.hospital_system,
                region=target.region,
                priority=target.priority,
                domain=target.domain,
                source_status=(
                    known_source.status
                    if known_source
                    else "indexed_source_url"
                    if indexed_source_url
                    else "indexed_evidence_only"
                    if rows > 0
                    else "missing"
                ),
                mrf_url=known_source.mrf_url if known_source else indexed_source_url,
                current_search_ready_rows=rows,
                current_search_ready_procedures=procedures,
                engine_status=engine_status,
                next_action=next_action,
                notes=target.notes,
            )
        )
    return coverage


def summarize_coverage(rows: list[HospitalCoverage]) -> dict[str, int]:
    return {
        "target_hospitals": len(rows),
        "known_sources": sum(
            1 for row in rows if row.source_status not in {"missing", "indexed_evidence_only"}
        ),
        "search_ready_hospitals": sum(1 for row in rows if row.engine_status == "search_ready"),
        "source_known_needs_indexing": sum(1 for row in rows if row.engine_status == "source_known_needs_indexing"),
        "needs_discovery": sum(1 for row in rows if row.engine_status == "needs_discovery"),
        "priority_1_search_ready": sum(
            1 for row in rows if row.priority == 1 and row.engine_status == "search_ready"
        ),
    }
