from healthscan.translation import (
    FallbackProcedure,
    FallbackResponse,
    ProcedureTranslator,
)


class StructuredFallback:
    def translate(self, query: str, *, care_setting: str = "unknown") -> FallbackResponse:
        return FallbackResponse(
            candidates=(
                FallbackProcedure(
                    code="12345",
                    code_type="CPT",
                    plain_label="Fallback procedure",
                    confidence=0.91,
                    care_setting="outpatient",
                ),
            )
        )


class LowConfidenceFallback:
    def translate(self, query: str, *, care_setting: str = "unknown") -> FallbackResponse:
        return FallbackResponse(
            candidates=(
                FallbackProcedure(
                    code="999",
                    code_type="DRG",
                    plain_label="Possible procedure",
                    confidence=0.4,
                    care_setting="inpatient",
                ),
            ),
            clarifying_question="Can you be more specific?",
        )


def first_code(response):
    return response.candidates[0].codes[0]


def test_exact_mapping_returns_schema_compatible_code_fields() -> None:
    response = ProcedureTranslator().translate("Brain MRI")

    assert response.status == "match"
    assert response.candidates[0].plain_label == "Brain MRI"
    assert first_code(response).procedure_code == "70551"
    assert first_code(response).code_type == "CPT"
    assert response.elapsed_ms < 100


def test_synonym_maps_to_same_canonical_procedure() -> None:
    response = ProcedureTranslator().translate("total knee arthroplasty")

    assert response.status == "match"
    assert response.candidates[0].plain_label == "Knee replacement"
    assert first_code(response).procedure_code == "470"


def test_ambiguous_input_returns_multiple_candidates() -> None:
    response = ProcedureTranslator().translate("stomach surgery")

    assert response.status == "ambiguous"
    assert len(response.candidates) > 1
    assert response.clarifying_question


def test_invalid_input_fails_gracefully() -> None:
    response = ProcedureTranslator().translate("banana phone")

    assert response.status == "not_found"
    assert response.message


def test_care_setting_filters_drg_vs_cpt_codes() -> None:
    inpatient = ProcedureTranslator().translate("knee replacement", care_setting="inpatient")
    outpatient = ProcedureTranslator().translate("knee replacement", care_setting="outpatient")

    assert [code.code_type for code in inpatient.candidates[0].codes] == ["DRG"]
    assert [code.code_type for code in outpatient.candidates[0].codes] == ["CPT"]
    assert outpatient.candidates[0].codes[0].procedure_code == "27447"


def test_provider_agnostic_fallback_accepts_structured_response() -> None:
    response = ProcedureTranslator(fallback=StructuredFallback()).translate("rare outpatient procedure")

    assert response.status == "match"
    assert response.source == "fallback"
    assert first_code(response).code_type == "CPT"
    assert first_code(response).procedure_code == "12345"


def test_low_confidence_fallback_asks_for_clarification() -> None:
    response = ProcedureTranslator(fallback=LowConfidenceFallback()).translate("rare inpatient thing")

    assert response.status == "clarify"
    assert response.clarifying_question == "Can you be more specific?"
