from healthscan.layer4 import (
    KnownSource,
    Layer4Target,
    coverage_for_targets,
    normalize_name,
    summarize_coverage,
)


def test_normalize_name_ignores_punctuation_and_case() -> None:
    assert normalize_name("Rady Children's Hospital") == "rady children s hospital"


def test_coverage_classifies_search_ready_source_known_and_discovery() -> None:
    targets = [
        Layer4Target("Ready Hospital", "Ready System", "ready.example", "Test", 1, ""),
        Layer4Target("Known Hospital", "Known System", "known.example", "Test", 1, ""),
        Layer4Target("Missing Hospital", "Missing System", "missing.example", "Test", 2, ""),
    ]
    sources = {
        normalize_name("Known System"): KnownSource(
            source_url="https://known.example/price",
            mrf_url="https://known.example/mrf.json",
            status="verified",
            notes="",
        )
    }
    search_counts = {normalize_name("Ready Hospital"): (3, 2, "https://ready.example/mrf.csv")}

    coverage = coverage_for_targets(targets, sources=sources, search_counts=search_counts)

    assert coverage[0].engine_status == "search_ready"
    assert coverage[1].engine_status == "source_known_needs_indexing"
    assert coverage[2].engine_status == "needs_discovery"


def test_summarize_coverage_counts_layer4_statuses() -> None:
    targets = [
        Layer4Target("Ready Hospital", "Ready System", "ready.example", "Test", 1, ""),
        Layer4Target("Known Hospital", "Known System", "known.example", "Test", 1, ""),
    ]
    coverage = coverage_for_targets(
        targets,
        sources={
            normalize_name("Known System"): KnownSource(
                source_url="https://known.example/price",
                mrf_url="https://known.example/mrf.json",
                status="verified",
                notes="",
            )
        },
        search_counts={normalize_name("Ready Hospital"): (3, 2, "https://ready.example/mrf.csv")},
    )

    summary = summarize_coverage(coverage)

    assert summary["target_hospitals"] == 2
    assert summary["known_sources"] == 2
    assert summary["search_ready_hospitals"] == 1
    assert summary["source_known_needs_indexing"] == 1
    assert summary["needs_discovery"] == 0
