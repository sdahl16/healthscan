from pathlib import Path

from healthscan.streaming_json import (
    object_fragments_for_code,
    records_from_large_json_file,
    records_from_large_json_file_for_codes,
)


def workspace_tmp_path(name: str) -> Path:
    path = Path("data") / "tmp" / "tests" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def test_object_fragments_for_code_finds_match_across_chunks() -> None:
    path = workspace_tmp_path("streaming-large.json")
    filler = "x" * 300
    path.write_text(
        """
        {"items": [
          {"description":"Ignore me","code_information":[{"code":"999","type":"CPT"}]},
        """
        + filler
        + """
          {"description":"Cesarean Section","code_information":[{"code":"783","type":"MS-DRG"}],
           "standard_charges":[{"minimum":2.46,"maximum":57744.25,"gross_charge":97580.87,
           "discounted_cash":53669.48,"setting":"inpatient","payers_information":[
           {"payer_name":"Aetna","plan_name":"PPO","standard_charge_dollar":30940.23}]}]}
        ]}
        """,
        encoding="utf-8",
    )

    fragments = object_fragments_for_code(
        path,
        code_type="DRG",
        code="783",
        chunk_size=250,
        overlap=1000,
    )

    assert len(fragments) == 1
    assert "Cesarean Section" in fragments[0]


def test_records_from_large_json_file_normalizes_prices() -> None:
    path = workspace_tmp_path("streaming-normalize.json")
    path.write_text(
        """
        {"description":"Emergency department visit","code_information":[{"code":"99285","type":"CPT"}],
        "standard_charges":[{"minimum":16.83,"maximum":779.00,"gross_charge":14734.30,
        "discounted_cash":8103.87,"setting":"outpatient","payers_information":[
        {"payer_name":"Blue Cross","plan_name":"PPO","standard_charge_dollar":7322.95}]}]}
        """,
        encoding="utf-8",
    )

    records = records_from_large_json_file(path, code_type="CPT", code="99285")

    assert records[0]["description"] == "Emergency department visit"
    assert records[0]["standard_charge|negotiated_dollar"] == 7322.95


def test_records_from_large_json_file_for_codes_scans_once_for_multiple_targets() -> None:
    path = workspace_tmp_path("streaming-multi.json")
    path.write_text(
        """
        {"items": [
        {"description":"Chest X-ray","code_information":[{"code":"71046","type":"CPT"}],
        "standard_charges":[{"gross_charge":900,"discounted_cash":300,"setting":"outpatient",
        "payers_information":[{"payer_name":"Aetna","plan_name":"PPO","standard_charge_dollar":120}]}]},
        {"description":"EKG","code_information":[{"code":"93000","type":"CPT"}],
        "standard_charges":[{"gross_charge":200,"discounted_cash":100,"setting":"outpatient",
        "payers_information":[{"payer_name":"Aetna","plan_name":"PPO","standard_charge_dollar":80}]}]}
        ]}
        """,
        encoding="utf-8",
    )

    records = records_from_large_json_file_for_codes(
        path,
        targets=[("CPT", "71046"), ("CPT", "93000")],
    )

    assert records[("CPT", "71046")][0]["description"] == "Chest X-ray"
    assert records[("CPT", "93000")][0]["description"] == "EKG"
