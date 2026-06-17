from __future__ import annotations

import json

from scripts.build_translation_expansion_report import (
    _safe_json_preview,
    build_candidate_rows,
    build_gap_rows,
    mapping_coverage,
    primary_swap_candidates,
)


def test_safe_json_preview_returns_only_expansion_fields() -> None:
    preview = _safe_json_preview(
        json.dumps(
            [
                {
                    "plain_name": "Vitrectomy",
                    "procedure_code": "67036",
                    "code_type": "CPT",
                    "setting": "outpatient",
                    "reason": "Extra text not needed for expansion report",
                }
            ]
        )
    )

    assert preview == [
        {
            "plain_name": "Vitrectomy",
            "procedure_code": "67036",
            "code_type": "CPT",
            "setting": "outpatient",
        }
    ]


def test_mapping_coverage_includes_code_level_index_counts() -> None:
    rows = mapping_coverage()

    colonoscopy = next(row for row in rows if row["plain_name"] == "Colonoscopy")
    assert colonoscopy["primary_code_type"] == "CPT"
    assert colonoscopy["primary_code"] == "45378"
    assert colonoscopy["codes"][0]["code_type"] == "CPT"
    assert "indexed_hospitals" in colonoscopy["codes"][0]


def test_candidate_rows_are_supported_and_actionable() -> None:
    rows = build_candidate_rows()

    assert rows
    assert {row["primary_code_type"] for row in rows} <= {"CPT", "DRG", "HCPCS"}
    assert {row["recommendation"] for row in rows} <= {
        "add_to_lookup",
        "review_for_lookup",
        "cms_gap",
        "already_mapped",
    }


def test_gap_rows_include_unindexed_primary_lookup_codes() -> None:
    rows = build_gap_rows(
        [
            {
                "plain_name": "Example procedure",
                "primary_code_type": "CPT",
                "primary_code": "11111",
                "setting": "outpatient",
                "primary_indexed_hospitals": 0,
                "any_indexed_hospitals": 0,
                "codes": [
                    {"code_type": "CPT", "procedure_code": "11111", "indexed_hospitals": 0, "is_primary": True},
                ],
            }
        ]
    )

    assert rows
    assert all(row["primary_indexed_hospitals"] == 0 for row in rows)
    assert {row["priority"] for row in rows}


def test_primary_swap_candidates_find_indexed_alternates() -> None:
    rows = primary_swap_candidates(
        [
            {
                "plain_name": "Example procedure",
                "primary_code_type": "CPT",
                "primary_code": "11111",
                "setting": "outpatient",
                "primary_indexed_hospitals": 0,
                "any_indexed_hospitals": 4,
                "codes": [
                    {"code_type": "CPT", "procedure_code": "11111", "indexed_hospitals": 0, "is_primary": True},
                    {"code_type": "CPT", "procedure_code": "22222", "indexed_hospitals": 4, "is_primary": False},
                ],
            }
        ]
    )

    assert rows == [
        {
            "plain_name": "Example procedure",
            "current_primary": "CPT:11111",
            "suggested_primary": "CPT:22222",
            "suggested_indexed_hospitals": 4,
            "reason": "alternate_code_has_indexed_coverage",
        }
    ]
