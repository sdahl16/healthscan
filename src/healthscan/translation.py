from __future__ import annotations

import csv
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MAPPING_PATH = ROOT / "data" / "reference" / "procedure_mapping.csv"

CareSetting = Literal["inpatient", "outpatient", "unknown"]
TranslationStatus = Literal["match", "ambiguous", "clarify", "not_found"]


@dataclass(frozen=True)
class ProcedureCode:
    procedure_code: str
    code_type: str
    plain_label: str
    care_setting: CareSetting = "unknown"
    is_primary: bool = False


@dataclass(frozen=True)
class TranslationCandidate:
    plain_label: str
    confidence: float
    match_reason: str
    codes: tuple[ProcedureCode, ...]


@dataclass(frozen=True)
class TranslationResponse:
    query: str
    status: TranslationStatus
    candidates: tuple[TranslationCandidate, ...] = ()
    clarifying_question: str | None = None
    message: str | None = None
    source: str = "lookup"
    elapsed_ms: float = 0.0


@dataclass(frozen=True)
class FallbackProcedure:
    code: str
    code_type: str
    plain_label: str
    confidence: float
    care_setting: CareSetting = "unknown"


@dataclass(frozen=True)
class FallbackResponse:
    candidates: tuple[FallbackProcedure, ...] = ()
    clarifying_question: str | None = None
    message: str | None = None


class TranslationFallback(Protocol):
    def translate(self, query: str, *, care_setting: CareSetting = "unknown") -> FallbackResponse:
        """Return structured fallback candidates from any external model/provider."""


@dataclass(frozen=True)
class ProcedureMapping:
    plain_label: str
    primary_code_type: str
    primary_code: str
    alternate_codes: tuple[ProcedureCode, ...] = ()
    notes: str | None = None
    synonyms: tuple[str, ...] = ()
    tokens: frozenset[str] = field(default_factory=frozenset)

    @property
    def codes(self) -> tuple[ProcedureCode, ...]:
        primary = ProcedureCode(
            procedure_code=self.primary_code,
            code_type=self.primary_code_type,
            plain_label=self.plain_label,
            care_setting=setting_for_code_type(self.primary_code_type),
            is_primary=True,
        )
        return (primary, *self.alternate_codes)


DEFAULT_SYNONYMS = {
    "Hip replacement": ("hip surgery", "total hip", "total hip arthroplasty", "hip arthroplasty"),
    "Knee replacement": ("knee surgery", "total knee", "total knee arthroplasty", "knee arthroplasty"),
    "Colonoscopy": ("colon scope", "colon cancer screening", "screening colonoscopy"),
    "Vaginal delivery": ("normal delivery", "childbirth", "labor and delivery", "vaginal birth"),
    "C-section": ("cesarean", "cesarean section", "c section", "csection"),
    "Appendectomy": ("appendix removal", "appendix surgery", "lap appendectomy"),
    "Cardiac catheterization": ("heart cath", "cardiac cath", "coronary angiography"),
    "Brain MRI": ("mri brain", "head mri", "brain scan"),
    "CT abdomen and pelvis": ("ct abdomen pelvis", "abdominal ct", "ct belly", "stomach ct"),
    "Emergency department visit": ("er visit", "emergency room visit", "emergency visit", "ed visit"),
    "Gallbladder removal": ("cholecystectomy", "gall bladder surgery", "gallbladder surgery"),
    "Hernia repair": ("hernia surgery", "inguinal hernia repair"),
    "Hysterectomy": ("uterus removal", "remove uterus"),
    "Cataract surgery": ("cataract removal", "lens implant"),
    "Upper endoscopy": ("egd", "endoscopy", "upper gi scope"),
    "Screening mammogram": ("mammography", "mammogram"),
    "Chest X-ray": ("chest xray", "chest radiograph", "cxr"),
    "Abdominal ultrasound": ("belly ultrasound", "abdomen ultrasound"),
    "Echocardiogram": ("echo", "heart ultrasound"),
    "EKG": ("ecg", "electrocardiogram"),
    "Physical therapy evaluation": ("pt evaluation", "physical therapy eval"),
    "Complete blood count": ("cbc", "blood count"),
    "Basic metabolic panel": ("bmp", "metabolic panel"),
    "Lipid panel": ("cholesterol test", "cholesterol panel"),
    "Hemoglobin A1c": ("a1c", "hba1c", "diabetes blood test"),
    "COVID test": ("covid pcr", "coronavirus test"),
    "Sleep study": ("polysomnography", "sleep apnea test"),
    "Tonsillectomy": ("tonsil removal", "remove tonsils"),
    "Mastectomy": ("breast removal", "breast cancer surgery"),
    "Prostate biopsy": ("prostate needle biopsy",),
}

AMBIGUOUS_HINTS = {
    "stomach surgery": ("Appendectomy", "Gallbladder removal", "Hernia repair", "Upper endoscopy"),
    "heart test": ("Cardiac catheterization", "Echocardiogram", "EKG"),
    "scan": ("Brain MRI", "CT abdomen and pelvis", "Chest X-ray", "Abdominal ultrasound"),
    "blood test": ("Complete blood count", "Basic metabolic panel", "Lipid panel", "Hemoglobin A1c"),
    "delivery": ("Vaginal delivery", "C-section"),
}


def normalize_query(value: str) -> str:
    text = value.lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def token_set(value: str) -> frozenset[str]:
    stopwords = {"and", "or", "of", "the", "a", "an", "with", "without", "for", "to"}
    return frozenset(token for token in normalize_query(value).split() if token not in stopwords)


def setting_for_code_type(code_type: str) -> CareSetting:
    normalized = code_type.upper()
    if normalized in {"DRG", "MS-DRG", "MSDRG"}:
        return "inpatient"
    if normalized in {"CPT", "HCPCS"}:
        return "outpatient"
    return "unknown"


def parse_code(value: str, *, plain_label: str) -> ProcedureCode:
    parts = value.strip().split()
    if len(parts) != 2:
        raise ValueError(f"Unsupported code value: {value!r}")
    code_type, code = parts
    return ProcedureCode(
        procedure_code=code,
        code_type=code_type.upper(),
        plain_label=plain_label,
        care_setting=setting_for_code_type(code_type),
    )


def load_mappings(path: Path = DEFAULT_MAPPING_PATH) -> tuple[ProcedureMapping, ...]:
    mappings: list[ProcedureMapping] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            label = row["plain_language_name"].strip()
            alternates = tuple(
                parse_code(code.strip(), plain_label=label)
                for code in row.get("alternate_codes", "").split(";")
                if code.strip()
            )
            synonyms = DEFAULT_SYNONYMS.get(label, ())
            token_values = [label, *synonyms]
            mappings.append(
                ProcedureMapping(
                    plain_label=label,
                    primary_code_type=row["primary_code_type"].strip().upper(),
                    primary_code=row["primary_code"].strip(),
                    alternate_codes=alternates,
                    notes=row.get("notes") or None,
                    synonyms=synonyms,
                    tokens=frozenset().union(*(token_set(value) for value in token_values)),
                )
            )
    return tuple(mappings)


def _filter_codes(codes: tuple[ProcedureCode, ...], care_setting: CareSetting) -> tuple[ProcedureCode, ...]:
    if care_setting == "unknown":
        return codes
    filtered = tuple(code for code in codes if code.care_setting == care_setting or code.care_setting == "unknown")
    return filtered or codes


class ProcedureTranslator:
    def __init__(
        self,
        *,
        mapping_path: Path = DEFAULT_MAPPING_PATH,
        fallback: TranslationFallback | None = None,
        low_confidence_threshold: float = 0.72,
    ) -> None:
        self.mappings = load_mappings(mapping_path)
        self.fallback = fallback
        self.low_confidence_threshold = low_confidence_threshold
        self._by_normalized: dict[str, ProcedureMapping] = {}
        for mapping in self.mappings:
            self._by_normalized[normalize_query(mapping.plain_label)] = mapping
            for synonym in mapping.synonyms:
                self._by_normalized[normalize_query(synonym)] = mapping

    def translate(self, query: str, *, care_setting: CareSetting = "unknown") -> TranslationResponse:
        started = time.perf_counter()
        normalized = normalize_query(query)
        if not normalized:
            return self._finish(
                query,
                started,
                TranslationResponse(
                    query=query,
                    status="not_found",
                    message="Enter a procedure name, symptom-related procedure, or billing-code description.",
                ),
            )

        exact = self._by_normalized.get(normalized)
        if exact:
            return self._finish(
                query,
                started,
                TranslationResponse(
                    query=query,
                    status="match",
                    candidates=(self._candidate(exact, 1.0, "exact_or_synonym", care_setting),),
                ),
            )

        ambiguous = self._ambiguous_candidates(normalized, care_setting)
        if ambiguous:
            return self._finish(
                query,
                started,
                TranslationResponse(
                    query=query,
                    status="ambiguous",
                    candidates=ambiguous,
                    clarifying_question="Which procedure did you mean?",
                ),
            )

        scored = self._score_candidates(normalized, care_setting)
        if len(scored) > 1 and scored[0].confidence - scored[1].confidence < 0.08 and scored[0].confidence >= 0.45:
            return self._finish(
                query,
                started,
                TranslationResponse(
                    query=query,
                    status="ambiguous",
                    candidates=tuple(scored[:4]),
                    clarifying_question="Which of these procedures best matches what you need?",
                ),
            )
        if scored and scored[0].confidence >= self.low_confidence_threshold:
            return self._finish(
                query,
                started,
                TranslationResponse(query=query, status="match", candidates=(scored[0],)),
            )
        if scored and scored[0].confidence >= 0.45:
            return self._finish(
                query,
                started,
                TranslationResponse(
                    query=query,
                    status="clarify",
                    candidates=tuple(scored[:3]),
                    clarifying_question="Can you describe the body area, setting, or exact procedure?",
                ),
            )

        fallback_response = self._fallback(query, care_setting)
        if fallback_response:
            return self._finish(query, started, fallback_response)

        return self._finish(
            query,
            started,
            TranslationResponse(
                query=query,
                status="not_found",
                message="I could not match that to a supported procedure. Try a more specific procedure name.",
            ),
        )

    def _candidate(
        self,
        mapping: ProcedureMapping,
        confidence: float,
        match_reason: str,
        care_setting: CareSetting,
    ) -> TranslationCandidate:
        return TranslationCandidate(
            plain_label=mapping.plain_label,
            confidence=round(confidence, 3),
            match_reason=match_reason,
            codes=_filter_codes(mapping.codes, care_setting),
        )

    def _ambiguous_candidates(
        self,
        normalized_query: str,
        care_setting: CareSetting,
    ) -> tuple[TranslationCandidate, ...]:
        labels = AMBIGUOUS_HINTS.get(normalized_query)
        if not labels:
            return ()
        by_label = {mapping.plain_label: mapping for mapping in self.mappings}
        return tuple(
            self._candidate(by_label[label], 0.62, "known_ambiguous_phrase", care_setting)
            for label in labels
            if label in by_label
        )

    def _score_candidates(self, normalized_query: str, care_setting: CareSetting) -> list[TranslationCandidate]:
        query_tokens = token_set(normalized_query)
        if not query_tokens:
            return []
        scored: list[TranslationCandidate] = []
        for mapping in self.mappings:
            overlap = len(query_tokens & mapping.tokens)
            if overlap == 0:
                continue
            precision = overlap / len(query_tokens)
            recall = overlap / len(mapping.tokens)
            score = (0.65 * precision) + (0.35 * recall)
            if normalize_query(mapping.plain_label) in normalized_query:
                score = max(score, 0.86)
            scored.append(self._candidate(mapping, score, "token_similarity", care_setting))
        return sorted(scored, key=lambda item: item.confidence, reverse=True)

    def _fallback(self, query: str, care_setting: CareSetting) -> TranslationResponse | None:
        if self.fallback is None:
            return None
        response = self.fallback.translate(query, care_setting=care_setting)
        valid_candidates = []
        for candidate in response.candidates:
            if not candidate.code or not candidate.code_type or not candidate.plain_label:
                continue
            code_type = candidate.code_type.upper()
            valid_candidates.append(
                TranslationCandidate(
                    plain_label=candidate.plain_label,
                    confidence=round(candidate.confidence, 3),
                    match_reason="provider_fallback",
                    codes=(
                        ProcedureCode(
                            procedure_code=candidate.code,
                            code_type=code_type,
                            plain_label=candidate.plain_label,
                            care_setting=candidate.care_setting,
                            is_primary=True,
                        ),
                    ),
                )
            )
        if not valid_candidates:
            return TranslationResponse(
                query=query,
                status="not_found",
                message=response.message or "Fallback provider did not return a structured procedure match.",
                source="fallback",
            )
        if max(candidate.confidence for candidate in valid_candidates) < self.low_confidence_threshold:
            return TranslationResponse(
                query=query,
                status="clarify",
                candidates=tuple(valid_candidates[:3]),
                clarifying_question=response.clarifying_question
                or "Can you provide a more specific procedure name?",
                source="fallback",
            )
        return TranslationResponse(
            query=query,
            status="match",
            candidates=tuple(valid_candidates[:3]),
            source="fallback",
        )

    def _finish(self, query: str, started: float, response: TranslationResponse) -> TranslationResponse:
        elapsed_ms = (time.perf_counter() - started) * 1000
        return TranslationResponse(
            query=query,
            status=response.status,
            candidates=response.candidates,
            clarifying_question=response.clarifying_question,
            message=response.message,
            source=response.source,
            elapsed_ms=round(elapsed_ms, 3),
        )


def response_to_dict(response: TranslationResponse) -> dict[str, Any]:
    return {
        "query": response.query,
        "status": response.status,
        "clarifying_question": response.clarifying_question,
        "message": response.message,
        "source": response.source,
        "elapsed_ms": response.elapsed_ms,
        "candidates": [
            {
                "plain_label": candidate.plain_label,
                "confidence": candidate.confidence,
                "match_reason": candidate.match_reason,
                "codes": [
                    {
                        "procedure_code": code.procedure_code,
                        "code_type": code.code_type,
                        "plain_label": code.plain_label,
                        "care_setting": code.care_setting,
                        "is_primary": code.is_primary,
                    }
                    for code in candidate.codes
                ],
            }
            for candidate in response.candidates
        ],
    }
