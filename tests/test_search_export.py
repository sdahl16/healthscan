from healthscan.search_export import (
    record_from_csv_sample,
    record_from_dict_sample,
    records_from_json_fragment,
    records_from_providence_snippet,
    search_result_from_record,
    search_results_from_record,
)


def test_record_from_csv_sample_maps_standard_charge_fields() -> None:
    sample = (
        '"Brain MRI","PX-1","CDM","70551","CPT","0611","RC","","","both","","",'
        '3652.13,913.03,"Medicare","HMO","",306.88,"algorithm",,,,,'
        '"0","other",118.68,2921.70,"note"'
    )

    record = record_from_csv_sample(sample)

    assert record["description"] == "Brain MRI"
    assert record["standard_charge|gross"] == "3652.13"
    assert record["standard_charge|discounted_cash"] == "913.03"
    assert record["payer_name"] == "Medicare"


def test_record_from_csv_sample_maps_keck_shifted_fields() -> None:
    sample = (
        '"Appendectomy","341","MS-DRG","","","","","","","facility","inpatient",'
        '"","","","","","Blue Shield","Commercial","56285.69","","","","","","",'
        '"fee schedule","42216.59","58628.99",""'
    )

    record = record_from_csv_sample(sample)

    assert record["setting"] == "inpatient"
    assert record["payer_name"] == "Blue Shield"
    assert record["standard_charge|negotiated_dollar"] == "56285.69"


def test_record_from_csv_sample_maps_sharp_shifted_fields() -> None:
    sample = (
        '"C-section","783","MS-DRG","","","","","",'
        '"Inpatient","","","156034.80","117026.10","Multiplan","Multiplan",'
        '"107664.01","","","","","","","percent of total billed charges",'
        '"47590.61","127948.53","note"'
    )

    record = record_from_csv_sample(sample)

    assert record["setting"] == "Inpatient"
    assert record["standard_charge|gross"] == "156034.80"
    assert record["standard_charge|negotiated_dollar"] == "107664.01"


def test_record_from_dict_sample_parses_rady_sample() -> None:
    sample = "{'description': 'Rch Ed Visit Level V', 'standard_charge|gross': '5400'}"

    record = record_from_dict_sample(sample)

    assert record["description"] == "Rch Ed Visit Level V"
    assert record["standard_charge|gross"] == "5400"


def test_search_results_from_record_keeps_cash_and_negotiated_prices() -> None:
    record = {
        "description": "Diagnostic colonoscopy",
        "standard_charge|gross": "10000",
        "standard_charge|discounted_cash": "5000",
        "standard_charge|negotiated_dollar": "3000",
        "payer_name": "Blue Cross",
        "plan_name": "Commercial PPO",
    }

    results = search_results_from_record(
        record,
        hospital="Example Hospital",
        procedure_name="Colonoscopy",
        code_type="CPT",
        code="45378",
        source_url="https://example.org/mrf.csv",
        evidence_source="test",
    )

    assert [(result.display_price_type, result.display_price) for result in results] == [
        ("cash", 5000),
        ("negotiated", 3000),
    ]
    cash, negotiated = results
    assert cash.payer_name is None
    assert cash.plan_name is None
    assert negotiated.payer_name == "Blue Cross"
    assert negotiated.plan_name == "Commercial PPO"


def test_search_result_from_record_keeps_legacy_negotiated_headline_behavior() -> None:
    record = {
        "description": "Diagnostic colonoscopy",
        "standard_charge|gross": "10000",
        "standard_charge|discounted_cash": "5000",
        "standard_charge|negotiated_dollar": "3000",
        "payer_name": "Blue Cross",
    }

    result = search_result_from_record(
        record,
        hospital="Example Hospital",
        procedure_name="Colonoscopy",
        code_type="CPT",
        code="45378",
        source_url="https://example.org/mrf.csv",
        evidence_source="test",
    )

    assert result is not None
    assert result.display_price == 3000
    assert result.display_price_type == "negotiated"
    assert result.data_quality_flag == "ok"


def test_records_from_providence_snippet_extracts_prices() -> None:
    snippet = (
        '""description"":""Appendectomy Without Complicated Principal Diagnosis With Mcc"",'
        '""minimum"":27683.22,""maximum"":137246.0,'
        '""payer_name"":""Blue Shield"",""plan_name"":""Hmo/Ppo/Epo"",'
        '""standard_charge_dollar"":42590.29'
    )

    records = records_from_providence_snippet(snippet)

    assert records[0]["description"].startswith("Appendectomy")
    assert records[0]["standard_charge|min"] == "27683.22"
    assert records[0]["standard_charge|negotiated_dollar"] == "42590.29"


def test_records_from_json_fragment_extracts_ucsd_prices() -> None:
    snippet = (
        ',""description"":""Cesarean Section With Sterilization With McC"",'
        '""standard_charges"":[{""minimum"":2.46,""maximum"":57744.25,'
        '""gross_charge"":97580.87,""discounted_cash"":53669.48,'
        '""setting"":""inpatient"",""payers_information"":[{'
        '""payer_name"":""UNITED HEALTHCARE [1088]"",'
        '""plan_name"":""HERITAGE PROVIDER NETWORK"",'
        '""standard_charge_dollar"":30940.23}]}]}'
    )

    records = records_from_json_fragment(snippet)

    assert records[0]["description"].startswith("Cesarean")
    assert records[0]["standard_charge|discounted_cash"] == "53669.48"
    assert records[0]["standard_charge|negotiated_dollar"] == "30940.23"
    assert records[0]["payer_name"] == "UNITED HEALTHCARE [1088]"
