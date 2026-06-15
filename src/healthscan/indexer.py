from __future__ import annotations

import csv
import json
import re
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PRICE_KEYS = {
    "gross": ("gross_charge", "gross charge", "standard_charge|gross"),
    "cash": (
        "discounted_cash_price",
        "cash_discounted_price",
        "discounted cash price",
        "standard_charge|discounted_cash",
    ),
    "negotiated": (
        "standard_charge_negotiated_dollar",
        "payer_specific_negotiated_charge_dollar",
        "negotiated_dollar",
        "standard_charge|negotiated_dollar",
    ),
    "negotiated_min": ("deidentified_min", "de-identified_min", "min_negotiated", "standard_charge|min"),
    "negotiated_max": ("deidentified_max", "de-identified_max", "max_negotiated", "standard_charge|max"),
    "median_allowed": ("median_allowed_amount", "median_amount"),
    "allowed_p10": ("tenth_percentile_allowed_amount", "10th_percentile_allowed_amount", "10th_percentile"),
    "allowed_p90": ("ninetieth_percentile_allowed_amount", "90th_percentile_allowed_amount", "90th_percentile"),
}

DEFAULT_LOW_OUTLIER_AMOUNT = 100.0
DEFAULT_HIGH_OUTLIER_AMOUNT = 500_000.0
INPATIENT_DRG_LOW_OUTLIER_AMOUNT = 1_000.0


@dataclass(frozen=True)
class IndexedPrice:
    procedure_name: str
    procedure_code: str
    code_type: str
    description: str | None
    setting: str | None
    price_type: str
    amount: float
    payer_name: str | None
    plan_name: str | None
    allowed_amount_count: int | None
    last_updated: str | None
    source_url: str
    data_quality_flag: str
    parse_warnings: str | None = None


def _norm(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "_").replace("-", "_")


def parse_amount(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, int | float):
        amount = float(value)
    else:
        text = str(value).strip()
        if not text:
            return None
        text = text.replace("$", "").replace(",", "")
        try:
            amount = float(text)
        except ValueError:
            return None
    if amount <= 0 or amount >= 999_999_999:
        return None
    return amount


def quality_flag_for_amount(*, amount: float, code_type: str, price_type: str) -> str:
    high_threshold = DEFAULT_HIGH_OUTLIER_AMOUNT
    low_threshold = DEFAULT_LOW_OUTLIER_AMOUNT
    if code_type.upper() in {"DRG", "MS-DRG", "MSDRG"}:
        low_threshold = INPATIENT_DRG_LOW_OUTLIER_AMOUNT

    if amount < low_threshold:
        return "low_outlier"
    if amount > high_threshold:
        return "high_outlier"
    if price_type in {"negotiated_min", "negotiated_max"} and amount == 999_999_999:
        return "placeholder_amount"
    return "ok"


def _first(record: dict[str, Any], names: Iterable[str]) -> Any:
    normalized = {_norm(key): value for key, value in record.items()}
    for name in names:
        value = normalized.get(_norm(name))
        if value not in (None, ""):
            return value
    return None


def _codes_from_record(record: dict[str, Any]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    code_type = _first(record, ("code_type", "type", "billing_code_type"))
    code = _first(record, ("code", "billing_code", "billing/accounting_code"))
    if code_type and code:
        pairs.append((str(code_type).upper(), str(code).strip()))

    for index in range(1, 10):
        indexed_code = record.get(f"code|{index}")
        indexed_type = record.get(f"code|{index}|type")
        if indexed_code and indexed_type:
            pairs.append((str(indexed_type).upper(), str(indexed_code).strip()))

    for value in record.values():
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    item_type = _first(item, ("code_type", "type"))
                    item_code = _first(item, ("code", "billing_code"))
                    if item_type and item_code:
                        pairs.append((str(item_type).upper(), str(item_code).strip()))
    return pairs


def record_matches(record: dict[str, Any], *, code_type: str, code: str) -> bool:
    wanted_type = code_type.upper()
    wanted_code = code.strip()
    for found_type, found_code in _codes_from_record(record):
        normalized_found_type = found_type.replace("-", "")
        normalized_wanted_type = wanted_type.replace("-", "")
        type_matches = normalized_found_type == normalized_wanted_type
        if wanted_type == "DRG" and found_type in {"MS-DRG", "MSDRG"}:
            type_matches = True
        if wanted_type == "CPT" and found_type == "HCPCS":
            type_matches = True
        if type_matches and found_code == wanted_code:
            return True
    return False


def _iter_dicts(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _iter_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_dicts(child)


def json_matching_records(path: Path, *, code_type: str, code: str) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return [record for record in _iter_dicts(data) if record_matches(record, code_type=code_type, code=code)]


def _looks_like_charge_header(row: list[str]) -> bool:
    normalized = {_norm(column) for column in row}
    return "description" in normalized and any(column.startswith("code|") for column in row)


def csv_matching_records(path: Path, *, code_type: str, code: str, limit: int | None = None) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        raw_reader = csv.reader(handle)
        header: list[str] | None = None
        for row in raw_reader:
            if _looks_like_charge_header(row):
                header = row
                break
        if header is None:
            return []
        reader = csv.DictReader(handle, fieldnames=header)
        for index, row in enumerate(reader):
            if limit is not None and index >= limit:
                break
            if record_matches(row, code_type=code_type, code=code):
                matches.append(row)
    return matches


def prices_from_record(
    record: dict[str, Any],
    *,
    procedure_name: str,
    procedure_code: str,
    code_type: str,
    source_url: str,
    last_updated: str | None,
) -> list[IndexedPrice]:
    description = _first(record, ("description", "standard_charge_description", "general_description"))
    setting = _first(record, ("setting",))
    payer_name = _first(record, ("payer_name", "payer"))
    plan_name = _first(record, ("plan_name", "plan"))
    allowed_count = _first(record, ("count_of_allowed_amounts", "allowed_amount_count", "count"))
    try:
        allowed_amount_count = int(allowed_count) if allowed_count not in (None, "") else None
    except ValueError:
        allowed_amount_count = None

    prices: list[IndexedPrice] = []
    for price_type, keys in PRICE_KEYS.items():
        amount = parse_amount(_first(record, keys))
        if amount is None:
            continue
        prices.append(
            IndexedPrice(
                procedure_name=procedure_name,
                procedure_code=procedure_code,
                code_type=code_type,
                description=str(description) if description else None,
                setting=str(setting) if setting else None,
                price_type=price_type,
                amount=amount,
                payer_name=str(payer_name) if payer_name else None,
                plan_name=str(plan_name) if plan_name else None,
                allowed_amount_count=allowed_amount_count,
                last_updated=last_updated,
                source_url=source_url,
                data_quality_flag=quality_flag_for_amount(amount=amount, code_type=code_type, price_type=price_type),
            )
        )
    return prices


def prices_from_standard_charge_item(
    item: dict[str, Any],
    *,
    procedure_name: str,
    procedure_code: str,
    code_type: str,
    source_url: str,
    last_updated: str | None,
) -> list[IndexedPrice]:
    prices: list[IndexedPrice] = []
    description = _first(item, ("description", "standard_charge_description", "general_description"))
    for charge in item.get("standard_charges", []) or []:
        if not isinstance(charge, dict):
            continue
        base = {
            "description": description,
            "setting": _first(charge, ("setting",)),
            "gross_charge": _first(charge, ("gross_charge",)),
            "discounted_cash_price": _first(charge, ("discounted_cash", "discounted_cash_price")),
            "deidentified_min": _first(charge, ("minimum",)),
            "deidentified_max": _first(charge, ("maximum",)),
        }
        prices.extend(
            prices_from_record(
                base,
                procedure_name=procedure_name,
                procedure_code=procedure_code,
                code_type=code_type,
                source_url=source_url,
                last_updated=last_updated,
            )
        )
        for payer in charge.get("payers_information", []) or []:
            if not isinstance(payer, dict):
                continue
            payer_record = {
                "description": description,
                "setting": _first(charge, ("setting",)),
                "payer_name": _first(payer, ("payer_name",)),
                "plan_name": _first(payer, ("plan_name",)),
                "standard_charge_negotiated_dollar": _first(payer, ("standard_charge_dollar",)),
                "allowed_amount_count": _first(payer, ("count",)),
            }
            prices.extend(
                prices_from_record(
                    payer_record,
                    procedure_name=procedure_name,
                    procedure_code=procedure_code,
                    code_type=code_type,
                    source_url=source_url,
                    last_updated=last_updated,
                )
            )
    return prices


def insert_prices(
    connection: sqlite3.Connection,
    *,
    hospital_id: int,
    mrf_source_id: int,
    prices: Iterable[IndexedPrice],
) -> int:
    rows = list(prices)
    connection.executemany(
        """
        INSERT INTO indexed_prices (
            hospital_id, mrf_source_id, procedure_name, procedure_code, code_type,
            description, setting, price_type, amount, payer_name, plan_name,
            allowed_amount_count, last_updated, source_url, data_quality_flag, parse_warnings
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                hospital_id,
                mrf_source_id,
                price.procedure_name,
                price.procedure_code,
                price.code_type,
                price.description,
                price.setting,
                price.price_type,
                price.amount,
                price.payer_name,
                price.plan_name,
                price.allowed_amount_count,
                price.last_updated,
                price.source_url,
                price.data_quality_flag,
                price.parse_warnings,
            )
            for price in rows
        ],
    )
    return len(rows)


def address_parts(address: str | None) -> tuple[str | None, str | None, str | None]:
    if not address:
        return None, None, None
    match = re.search(r"\b([A-Z]{2})\s+(\d{5}(?:-\d{4})?)\b", address)
    if not match:
        return address, None, None
    return address, match.group(1), match.group(2)
