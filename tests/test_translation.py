from healthscan.translation import (
    FallbackProcedure,
    FallbackResponse,
    ProcedureTranslator,
    normalize_code_type,
    response_to_dict,
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
    response = ProcedureTranslator().translate("MRI brain")

    assert response.status == "match"
    assert response.candidates[0].plain_label == "MRI brain"
    assert first_code(response).procedure_code == "70551"
    assert first_code(response).code_type == "CPT"
    assert first_code(response).setting == "outpatient"
    assert response.elapsed_ms < 100


def test_thin_procedure_mappings_include_valid_alternate_codes() -> None:
    translator = ProcedureTranslator()
    expected_codes = {
        "MRI brain": {("CPT", "70551"), ("CPT", "70552"), ("CPT", "70553")},
        "Colonoscopy": {("CPT", "45378"), ("CPT", "45380"), ("CPT", "45385"), ("HCPCS", "G0121")},
        "Emergency department visit": {("CPT", "99283"), ("CPT", "99284"), ("CPT", "99285")},
        "Appendectomy": {("CPT", "44950"), ("CPT", "44960"), ("CPT", "44970"), ("DRG", "341"), ("DRG", "342"), ("DRG", "343")},
        "C-section": {("DRG", "783"), ("DRG", "784"), ("DRG", "785"), ("DRG", "786"), ("DRG", "787"), ("DRG", "788")},
        "Vaginal delivery": {("DRG", "806"), ("DRG", "807")},
        "Hip replacement": {("DRG", "469"), ("DRG", "470"), ("CPT", "27130")},
        "Knee replacement": {("DRG", "469"), ("DRG", "470"), ("CPT", "27447")},
        "Cardiac catheterization": {("DRG", "286"), ("DRG", "287"), ("CPT", "93454"), ("CPT", "93458"), ("CPT", "93460")},
    }

    for procedure, expected in expected_codes.items():
        response = translator.translate(procedure)

        assert response.status == "match", procedure
        found = {(code.code_type, code.procedure_code) for code in response.candidates[0].codes}
        assert expected.issubset(found), procedure


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


def test_ambiguous_response_serializes_frontend_option_shape() -> None:
    payload = response_to_dict(ProcedureTranslator().translate("heart surgery"))

    assert payload["source"] == "clarification_needed"
    assert payload["prompt"] == "Which procedure did you mean?"
    assert len(payload["options"]) >= 2
    assert payload["options"][0] == {
        "label": "Coronary bypass (CABG)",
        "procedure_code": "231",
        "code_type": "DRG",
        "setting": "inpatient",
    }


def test_phase_three_ambiguous_inputs_never_single_guess() -> None:
    queries = [
        "heart surgery",
        "back surgery",
        "brain surgery",
        "stomach surgery",
        "cancer surgery",
        "women's surgery",
        "eye surgery",
        "shoulder surgery",
        "chest surgery",
        "abdominal surgery",
    ]

    translator = ProcedureTranslator()
    for query in queries:
        response = translator.translate(query)

        assert response.status == "ambiguous", query
        assert len(response.candidates) > 1, query


def test_invalid_input_fails_gracefully() -> None:
    response = ProcedureTranslator().translate("banana phone")

    assert response.status == "not_found"
    assert response.message


def test_care_setting_filters_drg_vs_cpt_codes() -> None:
    inpatient = ProcedureTranslator().translate("knee replacement", care_setting="inpatient")
    outpatient = ProcedureTranslator().translate("knee replacement", care_setting="outpatient")

    assert {code.code_type for code in inpatient.candidates[0].codes} == {"DRG"}
    assert {code.procedure_code for code in inpatient.candidates[0].codes} == {"469", "470"}
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


def test_code_type_normalization_rewrites_ms_drg_and_rejects_apc() -> None:
    assert normalize_code_type("MS-DRG") == "DRG"
    assert normalize_code_type("MSDRG") == "DRG"

    try:
        normalize_code_type("APC")
    except ValueError as error:
        assert "APC is not supported" in str(error)
    else:
        raise AssertionError("APC should be rejected")


def test_response_serialization_uses_setting_field() -> None:
    payload = response_to_dict(ProcedureTranslator().translate("screening colonoscopy"))
    code = payload["candidates"][0]["codes"][0]

    assert code["procedure_code"] == "G0121"
    assert code["code_type"] == "HCPCS"
    assert code["setting"] == "outpatient"
    assert "care_setting" not in code


def test_minor_misspelling_uses_fuzzy_match() -> None:
    response = ProcedureTranslator().translate("mamogram")

    assert response.status == "match"
    assert response.candidates[0].plain_label == "Mammogram"
    assert response.candidates[0].match_reason in {"exact_or_synonym", "fuzzy_name_or_synonym"}


def test_provider_fallback_rejects_unsupported_code_types() -> None:
    class UnsupportedFallback:
        def translate(self, query: str, *, care_setting: str = "unknown") -> FallbackResponse:
            return FallbackResponse(
                candidates=(
                    FallbackProcedure(
                        code="1234",
                        code_type="APC",
                        plain_label="Unsupported APC",
                        confidence=0.95,
                    ),
                )
            )

    response = ProcedureTranslator(fallback=UnsupportedFallback()).translate("unsupported procedure")

    assert response.status == "not_found"
