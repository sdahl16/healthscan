from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


EXCLUDED_QUALITY_FLAGS = {
    "low_outlier",
    "high_outlier",
    "placeholder_amount",
}


@dataclass(frozen=True)
class RelevanceAssessment:
    is_user_relevant: bool
    user_relevance_flag: str
    user_relevance_reason: str | None = None


def assess_price_relevance(row: Mapping[str, object]) -> RelevanceAssessment:
    quality_flag = str(row.get("data_quality_flag") or "ok").strip().lower()
    if quality_flag in EXCLUDED_QUALITY_FLAGS:
        return RelevanceAssessment(
            is_user_relevant=False,
            user_relevance_flag=f"excluded_{quality_flag}",
            user_relevance_reason="Filtered from patient-facing search because the displayed price is implausible or non-informative.",
        )
    return RelevanceAssessment(
        is_user_relevant=True,
        user_relevance_flag="display_ok",
    )
