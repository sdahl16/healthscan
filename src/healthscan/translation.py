from __future__ import annotations

import csv
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MAPPING_PATH = ROOT / "data" / "reference" / "procedure_mapping.csv"

Setting = Literal["inpatient", "outpatient", "either", "unknown"]
CareSetting = Setting
TranslationStatus = Literal["match", "ambiguous", "clarify", "not_found"]
SUPPORTED_CODE_TYPES = {"CPT", "DRG", "HCPCS"}


@dataclass(frozen=True)
class ProcedureCode:
    procedure_code: str
    code_type: str
    description: str
    setting: Setting = "unknown"
    is_primary: bool = False

    @property
    def plain_label(self) -> str:
        return self.description

    @property
    def care_setting(self) -> Setting:
        return self.setting


@dataclass(frozen=True)
class TranslationCandidate:
    description: str
    confidence: float
    match_reason: str
    codes: tuple[ProcedureCode, ...]

    @property
    def plain_label(self) -> str:
        return self.description


@dataclass(frozen=True)
class TranslationResponse:
    query: str
    status: TranslationStatus
    candidates: tuple[TranslationCandidate, ...] = ()
    clarifying_question: str | None = None
    message: str | None = None
    source: str = "lookup"
    elapsed_ms: float = 0.0


@dataclass(frozen=True, init=False)
class FallbackProcedure:
    code: str
    code_type: str
    confidence: float
    plain_label: str = ""
    description: str = ""
    setting: Setting = "unknown"

    def __init__(
        self,
        code: str,
        code_type: str,
        confidence: float,
        plain_label: str = "",
        description: str = "",
        setting: Setting = "unknown",
        care_setting: Setting | None = None,
    ) -> None:
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "code_type", code_type)
        object.__setattr__(self, "confidence", confidence)
        object.__setattr__(self, "plain_label", plain_label)
        object.__setattr__(self, "description", description or plain_label)
        object.__setattr__(self, "setting", care_setting or setting)

    @property
    def care_setting(self) -> Setting:
        return self.setting


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
    description: str
    primary_code_type: str
    primary_code: str
    setting: Setting = "unknown"
    alternate_codes: tuple[ProcedureCode, ...] = ()
    notes: str | None = None
    synonyms: tuple[str, ...] = ()
    tokens: frozenset[str] = field(default_factory=frozenset)

    @property
    def plain_label(self) -> str:
        return self.description

    @property
    def codes(self) -> tuple[ProcedureCode, ...]:
        primary = ProcedureCode(
            procedure_code=self.primary_code,
            code_type=self.primary_code_type,
            description=self.description,
            setting=self.setting,
            is_primary=True,
        )
        return (primary, *self.alternate_codes)


DEFAULT_SYNONYMS = {
    "Hip replacement": ("hip surgery", "total hip", "total hip arthroplasty", "hip arthroplasty"),
    "Knee replacement": ("knee surgery", "total knee", "total knee arthroplasty", "knee arthroplasty"),
    "Colonoscopy": ("colon scope", "colon cancer screening", "scope of the colon"),
    "Vaginal delivery": ("normal delivery", "childbirth", "labor and delivery", "vaginal birth"),
    "C-section": ("cesarean", "cesarean section", "c section", "csection"),
    "Appendectomy": ("appendix removal", "appendix surgery", "lap appendectomy", "appendectomy inpatient"),
    "Cardiac catheterization": ("heart cath", "cardiac cath", "coronary angiography"),
    "MRI brain": ("mri brain", "head mri", "brain scan", "brain mri"),
    "MRI spine": ("spine mri", "back mri", "lumbar mri"),
    "CT scan abdomen": ("ct abdomen pelvis", "abdominal ct", "ct belly", "stomach ct"),
    "Emergency department visit": ("er visit", "emergency room visit", "emergency visit", "ed visit"),
    "Gallbladder removal": ("cholecystectomy", "laparoscopic cholecystectomy", "gall bladder surgery", "gallbladder surgery", "gallbladder out"),
    "Gallbladder removal (open)": ("open cholecystectomy", "open gallbladder surgery"),
    "Hernia repair": ("hernia surgery", "inguinal hernia repair"),
    "Hysterectomy": ("uterus removal", "remove uterus"),
    "Cataract surgery": ("cataract removal", "lens implant"),
    "Upper endoscopy": ("egd", "endoscopy", "upper gi scope"),
    "Upper endoscopy with biopsy": ("egd biopsy", "upper endoscopy biopsy"),
    "Mammogram": ("mammography", "screening mammogram"),
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
    "Tonsillectomy (child)": ("child tonsillectomy", "pediatric tonsillectomy", "kids tonsils"),
    "Mastectomy": ("breast removal", "breast cancer surgery", "boob job removal"),
    "Breast lumpectomy": ("lumpectomy", "partial mastectomy", "breast lump removal"),
    "Screening colonoscopy": ("preventive colonoscopy", "colon cancer screening"),
    "Shoulder arthroscopy": ("rotator cuff repair", "shoulder scope"),
    "Knee arthroscopy": ("knee scope", "meniscus surgery"),
    "Carpal tunnel surgery": ("carpal tunnel release", "wrist nerve surgery"),
    "Coronary bypass (CABG)": ("cabg", "coronary bypass", "heart bypass"),
    "Prostate biopsy": ("prostate needle biopsy",),
}

AMBIGUOUS_HINTS = {
    "stomach surgery": ("Appendectomy", "Gallbladder removal", "Hernia repair", "Upper endoscopy"),
    "heart surgery": ("Coronary bypass (CABG)", "Cardiac catheterization"),
    "back surgery": ("MRI spine", "Hernia repair"),
    "brain surgery": ("MRI brain", "Emergency department visit"),
    "cancer surgery": ("Mastectomy", "Breast lumpectomy"),
    "womens surgery": ("C-section", "Vaginal delivery", "Mastectomy", "Breast lumpectomy"),
    "women s surgery": ("C-section", "Vaginal delivery", "Mastectomy", "Breast lumpectomy"),
    "eye surgery": ("Cataract surgery", "MRI brain"),
    "shoulder surgery": ("Shoulder arthroscopy", "MRI spine"),
    "chest surgery": ("Mastectomy", "Breast lumpectomy", "Coronary bypass (CABG)"),
    "abdominal surgery": ("Appendectomy", "Gallbladder removal", "Hernia repair"),
    "heart test": ("Cardiac catheterization", "Echocardiogram", "EKG"),
    "scan": ("MRI brain", "CT scan abdomen", "Mammogram"),
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


def normalize_code_type(code_type: str) -> str:
    normalized = re.sub(r"[^A-Z0-9]+", "-", code_type.strip().upper()).strip("-")
    if normalized in {"MS-DRG", "MSDRG"}:
        return "DRG"
    if normalized == "APC":
        raise ValueError("APC is not supported by the current CMS engine index.")
    if normalized not in SUPPORTED_CODE_TYPES:
        raise ValueError(f"Unsupported code_type: {code_type!r}")
    return normalized


def setting_for_code_type(code_type: str) -> Setting:
    normalized = normalize_code_type(code_type)
    if normalized == "DRG":
        return "inpatient"
    if normalized in {"CPT", "HCPCS"}:
        return "outpatient"
    return "unknown"


def parse_setting(value: str | None, code_type: str) -> Setting:
    normalized = (value or "").strip().lower()
    if normalized in {"inpatient", "outpatient", "either"}:
        return normalized  # type: ignore[return-value]
    return setting_for_code_type(code_type)


def parse_code(value: str, *, description: str, setting: Setting | None = None) -> ProcedureCode:
    raw = value.strip().replace(":", " ")
    parts = raw.split()
    if len(parts) != 2:
        raise ValueError(f"Unsupported code value: {value!r}")
    code_type, code = parts
    normalized_code_type = normalize_code_type(code_type)
    return ProcedureCode(
        procedure_code=code,
        code_type=normalized_code_type,
        description=description,
        setting=setting or setting_for_code_type(normalized_code_type),
    )


def _split_values(value: str, separators: str = r"[|;]") -> tuple[str, ...]:
    return tuple(part.strip() for part in re.split(separators, value or "") if part.strip())


def load_mappings(path: Path = DEFAULT_MAPPING_PATH) -> tuple[ProcedureMapping, ...]:
    mappings: list[ProcedureMapping] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            label = (row.get("plain_name") or row.get("plain_language_name") or "").strip()
            if not label:
                continue
            primary_code_type = normalize_code_type(row["primary_code_type"].strip())
            setting = parse_setting(row.get("setting"), primary_code_type)
            alternates = tuple(
                parse_code(code.strip(), description=label, setting=parse_setting(None, code.split(":", 1)[0].split()[0]))
                for code in _split_values(row.get("alternate_codes", ""))
                if code.strip()
            )
            synonyms = (*_split_values(row.get("synonyms", "")), *DEFAULT_SYNONYMS.get(label, ()))
            token_values = [label, *synonyms]
            mappings.append(
                ProcedureMapping(
                    description=label,
                    primary_code_type=primary_code_type,
                    primary_code=row["primary_code"].strip(),
                    setting=setting,
                    alternate_codes=alternates,
                    notes=row.get("notes") or None,
                    synonyms=synonyms,
                    tokens=frozenset().union(*(token_set(value) for value in token_values)),
                )
            )
    return tuple(mappings)


def _filter_codes(codes: tuple[ProcedureCode, ...], care_setting: CareSetting) -> tuple[ProcedureCode, ...]:
    if care_setting in {"unknown", "either"}:
        return codes
    filtered = tuple(code for code in codes if code.setting in {care_setting, "unknown", "either"})
    return filtered or codes


def levenshtein_distance(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)
    previous = list(range(len(right) + 1))
    for left_index, left_char in enumerate(left, start=1):
        current = [left_index]
        for right_index, right_char in enumerate(right, start=1):
            insertion = current[right_index - 1] + 1
            deletion = previous[right_index] + 1
            substitution = previous[right_index - 1] + (left_char != right_char)
            current.append(min(insertion, deletion, substitution))
        previous = current
    return previous[-1]


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
        self._match_terms: list[tuple[str, ProcedureMapping]] = []
        for mapping in self.mappings:
            self._by_normalized[normalize_query(mapping.plain_label)] = mapping
            self._match_terms.append((normalize_query(mapping.plain_label), mapping))
            for synonym in mapping.synonyms:
                self._by_normalized[normalize_query(synonym)] = mapping
                self._match_terms.append((normalize_query(synonym), mapping))

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

        fuzzy = self._fuzzy_candidate(normalized, care_setting)
        if fuzzy:
            return self._finish(
                query,
                started,
                TranslationResponse(query=query, status="match", candidates=(fuzzy,)),
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
            description=mapping.description,
            confidence=round(confidence, 3),
            match_reason=match_reason,
            codes=_filter_codes(mapping.codes, care_setting),
        )

    def _fuzzy_candidate(self, normalized_query: str, care_setting: CareSetting) -> TranslationCandidate | None:
        if len(normalized_query) < 5:
            return None
        matches: list[tuple[int, ProcedureMapping]] = []
        for term, mapping in self._match_terms:
            if abs(len(term) - len(normalized_query)) > 2:
                continue
            distance = levenshtein_distance(normalized_query, term)
            if distance <= 2:
                matches.append((distance, mapping))
        if not matches:
            return None
        matches.sort(key=lambda item: (item[0], item[1].plain_label))
        best_distance, best_mapping = matches[0]
        if len(matches) > 1 and matches[1][0] == best_distance and matches[1][1] != best_mapping:
            return None
        return self._candidate(best_mapping, 0.91 - (best_distance * 0.05), "fuzzy_name_or_synonym", care_setting)

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
            description = candidate.description or candidate.plain_label
            if not candidate.code or not candidate.code_type or not description:
                continue
            try:
                code_type = normalize_code_type(candidate.code_type)
            except ValueError:
                continue
            valid_candidates.append(
                TranslationCandidate(
                    description=description,
                    confidence=round(candidate.confidence, 3),
                    match_reason="provider_fallback",
                    codes=(
                        ProcedureCode(
                            procedure_code=candidate.code,
                            code_type=code_type,
                            description=description,
                            setting=parse_setting(candidate.setting, code_type),
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
    payload: dict[str, Any] = {
        "query": response.query,
        "status": response.status,
        "clarifying_question": response.clarifying_question,
        "message": response.message,
        "source": "clarification_needed" if response.status in {"ambiguous", "clarify"} else response.source,
        "elapsed_ms": response.elapsed_ms,
        "candidates": [
            {
                "description": candidate.description,
                "plain_label": candidate.plain_label,
                "confidence": candidate.confidence,
                "match_reason": candidate.match_reason,
                "codes": [
                    {
                        "procedure_code": code.procedure_code,
                        "code_type": code.code_type,
                        "description": code.description,
                        "plain_label": code.plain_label,
                        "setting": code.setting,
                        "is_primary": code.is_primary,
                    }
                    for code in candidate.codes
                ],
            }
            for candidate in response.candidates
        ],
    }
    if response.status in {"ambiguous", "clarify"}:
        payload["prompt"] = response.clarifying_question or "Did you mean one of these?"
        payload["options"] = [
            {
                "label": candidate.description,
                "procedure_code": code.procedure_code,
                "code_type": code.code_type,
                "setting": code.setting,
            }
            for candidate in response.candidates
            for code in candidate.codes[:1]
        ]
    return payload
