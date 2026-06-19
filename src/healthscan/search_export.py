from __future__ import annotations

import ast
import csv
import json
import re
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from healthscan.indexer import parse_amount, quality_flag_for_amount
from healthscan.relevance import assess_price_relevance


PRICE_FIELDNAMES = [
    "description",
    "code|1",
    "code|1|type",
    "code|2",
    "code|2|type",
    "code|3",
    "code|3|type",
    "billing_class",
    "setting",
    "drug_unit_of_measurement",
    "drug_type_of_measurement",
    "modifiers",
    "standard_charge|gross",
    "standard_charge|discounted_cash",
    "payer_name",
    "plan_name",
    "standard_charge|negotiated_dollar",
    "standard_charge|negotiated_percentage",
    "standard_charge|negotiated_algorithm",
    "median_amount",
    "10th_percentile",
    "90th_percentile",
    "count",
    "standard_charge|methodology",
    "standard_charge|min",
    "standard_charge|max",
    "additional_generic_notes",
]


@dataclass(frozen=True)
class SearchResult:
    hospital: str
    procedure_name: str
    code_type: str
    code: str
    description: str | None
    setting: str | None
    display_price: float
    display_price_type: str
    gross_price: float | None
    cash_price: float | None
    negotiated_price: float | None
    negotiated_min: float | None
    negotiated_max: float | None
    payer_name: str | None
    plan_name: str | None
    data_quality_flag: str
    user_relevance_flag: str
    user_relevance_reason: str | None
    source_url: str | None
    evidence_source: str


def _clean(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _amount(record: dict[str, Any], key: str) -> float | None:
    return parse_amount(record.get(key))


def _display_price(record: dict[str, Any]) -> tuple[float | None, str | None]:
    candidates = [
        ("standard_charge|negotiated_dollar", "negotiated"),
        ("standard_charge|discounted_cash", "cash"),
        ("standard_charge|min", "negotiated_min"),
        ("median_amount", "median_allowed"),
        ("standard_charge|gross", "gross"),
    ]
    for key, price_type in candidates:
        amount = _amount(record, key)
        if amount is not None:
            return amount, price_type
    return None, None


def _price_candidates(record: dict[str, Any]) -> list[tuple[str, float]]:
    cash = _amount(record, "standard_charge|discounted_cash")
    negotiated = _amount(record, "standard_charge|negotiated_dollar")
    candidates = [
        ("cash", cash),
        ("negotiated", negotiated),
    ]
    if cash is None and negotiated is None:
        candidates.extend(
            [
                ("negotiated_min", _amount(record, "standard_charge|min")),
                ("median_allowed", _amount(record, "median_amount")),
                ("gross", _amount(record, "standard_charge|gross")),
            ]
        )
    return [(price_type, amount) for price_type, amount in candidates if amount is not None]


def _result_for_price(
    record: dict[str, Any],
    *,
    hospital: str,
    procedure_name: str,
    code_type: str,
    code: str,
    source_url: str | None,
    evidence_source: str,
    display_price_type: str,
    display_price: float,
) -> SearchResult:
    data_quality_flag = quality_flag_for_amount(
        amount=display_price,
        code_type=code_type,
        price_type=display_price_type,
    )
    relevance = assess_price_relevance({"data_quality_flag": data_quality_flag})
    payer_name = None if display_price_type in {"cash", "gross"} else _clean(record.get("payer_name"))
    plan_name = None if display_price_type in {"cash", "gross"} else _clean(record.get("plan_name"))

    return SearchResult(
        hospital=hospital,
        procedure_name=procedure_name,
        code_type=code_type,
        code=code,
        description=_clean(record.get("description")),
        setting=_clean(record.get("setting")),
        display_price=display_price,
        display_price_type=display_price_type,
        gross_price=display_price if display_price_type == "gross" else None,
        cash_price=display_price if display_price_type == "cash" else None,
        negotiated_price=display_price if display_price_type == "negotiated" else None,
        negotiated_min=display_price if display_price_type == "negotiated_min" else None,
        negotiated_max=display_price if display_price_type == "negotiated_max" else None,
        payer_name=payer_name,
        plan_name=plan_name,
        data_quality_flag=data_quality_flag,
        user_relevance_flag=relevance.user_relevance_flag,
        user_relevance_reason=relevance.user_relevance_reason,
        source_url=source_url,
        evidence_source=evidence_source,
    )


def search_results_from_record(
    record: dict[str, Any],
    *,
    hospital: str,
    procedure_name: str,
    code_type: str,
    code: str,
    source_url: str | None,
    evidence_source: str,
) -> list[SearchResult]:
    return [
        _result_for_price(
            record,
            hospital=hospital,
            procedure_name=procedure_name,
            code_type=code_type,
            code=code,
            source_url=source_url,
            evidence_source=evidence_source,
            display_price_type=price_type,
            display_price=amount,
        )
        for price_type, amount in _price_candidates(record)
    ]


def search_result_from_record(
    record: dict[str, Any],
    *,
    hospital: str,
    procedure_name: str,
    code_type: str,
    code: str,
    source_url: str | None,
    evidence_source: str,
) -> SearchResult | None:
    display_price, display_price_type = _display_price(record)
    if display_price is None or display_price_type is None:
        return None
    return _result_for_price(
        record,
        hospital=hospital,
        procedure_name=procedure_name,
        code_type=code_type,
        code=code,
        source_url=source_url,
        evidence_source=evidence_source,
        display_price_type=display_price_type,
        display_price=display_price,
    )


def record_from_csv_sample(sample_line: str) -> dict[str, str]:
    values = next(csv.reader([sample_line]))
    if len(values) == 29 and values[9].lower() == "facility":
        return {
            "description": values[0],
            "code|1": values[1],
            "code|1|type": values[2],
            "billing_class": values[9],
            "setting": values[10],
            "payer_name": values[16],
            "plan_name": values[17],
            "standard_charge|negotiated_dollar": values[18],
            "standard_charge|methodology": values[25],
            "standard_charge|min": values[26],
            "standard_charge|max": values[27],
            "additional_generic_notes": values[28],
        }
    if len(values) == 26 and values[8]:
        return {
            "description": values[0],
            "code|1": values[1],
            "code|1|type": values[2],
            "setting": values[8],
            "standard_charge|gross": values[11],
            "standard_charge|discounted_cash": values[12],
            "payer_name": values[13],
            "plan_name": values[14],
            "standard_charge|negotiated_dollar": values[15],
            "standard_charge|methodology": values[22],
            "standard_charge|min": values[23],
            "standard_charge|max": values[24],
            "additional_generic_notes": values[25],
        }
    return {field: values[index] if index < len(values) else "" for index, field in enumerate(PRICE_FIELDNAMES)}


def record_from_dict_sample(sample_line: str) -> dict[str, Any]:
    parsed = ast.literal_eval(sample_line)
    if not isinstance(parsed, dict):
        raise ValueError("sample_line did not contain a dictionary")
    return parsed


def records_from_providence_snippet(sample_text: str) -> list[dict[str, Any]]:
    normalized_text = sample_text.replace('""', '"')
    records: list[dict[str, Any]] = []
    for match in re.finditer(
        r'"description"\s*:\s*"(?P<description>[^"]+)"(?P<body>.*?)(?="description"\s*:|$)',
        normalized_text,
        flags=re.DOTALL,
    ):
        body = match.group("body")
        record: dict[str, Any] = {"description": match.group("description"), "setting": "inpatient"}
        minimum = re.search(r'"minimum":(?P<amount>[0-9.]+)', body)
        maximum = re.search(r'"maximum":(?P<amount>[0-9.]+)', body)
        negotiated = re.search(r'"standard_charge_dollar":(?P<amount>[0-9.]+)', body)
        payer = re.search(r'"payer_name":"(?P<value>[^"]+)"', body)
        plan = re.search(r'"plan_name":"(?P<value>[^"]+)"', body)
        if minimum:
            record["standard_charge|min"] = minimum.group("amount")
        if maximum:
            record["standard_charge|max"] = maximum.group("amount")
        if negotiated:
            record["standard_charge|negotiated_dollar"] = negotiated.group("amount")
        if payer:
            record["payer_name"] = payer.group("value")
        if plan:
            record["plan_name"] = plan.group("value")
        if any(key in record for key in ("standard_charge|negotiated_dollar", "standard_charge|min")):
            records.append(record)
    return records


def records_from_json_fragment(sample_text: str) -> list[dict[str, Any]]:
    parsed_records = _records_from_json_object(sample_text)
    if parsed_records:
        return parsed_records

    normalized_text = sample_text.replace('""', '"')
    records: list[dict[str, Any]] = []
    for match in re.finditer(
        r'"description":"(?P<description>[^"]+)"(?P<body>.*?)(?="description"|$)',
        normalized_text,
        flags=re.DOTALL,
    ):
        body = match.group("body")
        record: dict[str, Any] = {"description": match.group("description")}
        fields = {
            "minimum": "standard_charge|min",
            "maximum": "standard_charge|max",
            "gross_charge": "standard_charge|gross",
            "discounted_cash": "standard_charge|discounted_cash",
            "standard_charge_dollar": "standard_charge|negotiated_dollar",
            "median_amount": "median_amount",
            "10th_percentile": "10th_percentile",
            "90th_percentile": "90th_percentile",
        }
        for source_key, target_key in fields.items():
            found = re.search(rf'"{re.escape(source_key)}"\s*:\s*(?P<amount>[0-9.]+)', body)
            if found:
                record[target_key] = found.group("amount")
        for source_key, target_key in {
            "setting": "setting",
            "payer_name": "payer_name",
            "plan_name": "plan_name",
        }.items():
            found = re.search(rf'"{re.escape(source_key)}"\s*:\s*"(?P<value>[^"]*)"', body)
            if found:
                record[target_key] = found.group("value")
        if any(key in record for key in ("standard_charge|negotiated_dollar", "standard_charge|discounted_cash")):
            records.append(record)
    return records


def _records_from_json_object(sample_text: str) -> list[dict[str, Any]]:
    try:
        item = json.loads(sample_text)
    except json.JSONDecodeError:
        return []
    if not isinstance(item, dict):
        return []
    description = _clean(item.get("description"))
    records: list[dict[str, Any]] = []
    for charge in item.get("standard_charges", []) or []:
        if not isinstance(charge, dict):
            continue
        base = {
            "description": description,
            "setting": charge.get("setting"),
            "standard_charge|min": charge.get("minimum"),
            "standard_charge|max": charge.get("maximum"),
            "standard_charge|gross": charge.get("gross_charge"),
            "standard_charge|discounted_cash": charge.get("discounted_cash"),
        }
        for payer in charge.get("payers_information", []) or []:
            if not isinstance(payer, dict):
                continue
            record = {
                **base,
                "payer_name": payer.get("payer_name"),
                "plan_name": payer.get("plan_name"),
                "standard_charge|negotiated_dollar": payer.get("standard_charge_dollar"),
                "median_amount": payer.get("median_amount"),
                "10th_percentile": payer.get("10th_percentile"),
                "90th_percentile": payer.get("90th_percentile"),
            }
            if any(record.get(key) not in (None, "") for key in ("standard_charge|negotiated_dollar", "standard_charge|discounted_cash")):
                records.append(record)
        if not charge.get("payers_information") and any(
            base.get(key) not in (None, "") for key in ("standard_charge|discounted_cash", "standard_charge|gross")
        ):
            records.append(base)
    return records


def best_results_from_indexed_prices(connection: sqlite3.Connection) -> list[SearchResult]:
    rows = connection.execute(
        """
        SELECT
            h.name AS hospital,
            p.procedure_name,
            p.procedure_code,
            p.code_type,
            p.description,
            p.setting,
            p.price_type,
            p.amount,
            p.payer_name,
            p.plan_name,
            p.source_url,
            p.data_quality_flag
        FROM indexed_prices p
        JOIN hospitals h ON h.id = p.hospital_id
        WHERE p.data_quality_flag IS NULL OR p.data_quality_flag != 'low_outlier'
        ORDER BY
            h.name,
            p.procedure_name,
            CASE p.price_type
                WHEN 'negotiated' THEN 1
                WHEN 'cash' THEN 2
                WHEN 'negotiated_min' THEN 3
                WHEN 'median_allowed' THEN 4
                WHEN 'gross' THEN 5
                ELSE 6
            END,
            p.amount
        """
    ).fetchall()
    seen: set[tuple[str, str]] = set()
    results: list[SearchResult] = []
    for row in rows:
        key = (row["hospital"], row["procedure_name"])
        if key in seen:
            continue
        seen.add(key)
        amount = float(row["amount"])
        results.append(
            SearchResult(
                hospital=row["hospital"],
                procedure_name=row["procedure_name"],
                code_type=row["code_type"],
                code=row["procedure_code"],
                description=row["description"],
                setting=row["setting"],
                display_price=amount,
                display_price_type=row["price_type"],
                gross_price=amount if row["price_type"] == "gross" else None,
                cash_price=amount if row["price_type"] == "cash" else None,
                negotiated_price=amount if row["price_type"] == "negotiated" else None,
                negotiated_min=amount if row["price_type"] == "negotiated_min" else None,
                negotiated_max=amount if row["price_type"] == "negotiated_max" else None,
                payer_name=row["payer_name"],
                plan_name=row["plan_name"],
                data_quality_flag=row["data_quality_flag"] or "ok",
                user_relevance_flag="display_ok",
                user_relevance_reason=None,
                source_url=row["source_url"],
                evidence_source="indexed_prices",
            )
        )
    return results


def dedupe_results(results: Iterable[SearchResult]) -> list[SearchResult]:
    best: dict[tuple[str, str], SearchResult] = {}
    rank = {"negotiated": 1, "cash": 2, "negotiated_min": 3, "median_allowed": 4, "gross": 5}
    for result in results:
        key = (result.hospital, result.procedure_name)
        current = best.get(key)
        if current is None or rank.get(result.display_price_type, 99) < rank.get(current.display_price_type, 99):
            best[key] = result
    return sorted(best.values(), key=lambda item: (item.procedure_name, item.hospital))
