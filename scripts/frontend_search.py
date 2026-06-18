from __future__ import annotations

import json
import math
import sqlite3
import sys
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from healthscan.database import DEFAULT_DB_PATH
from healthscan.translation import ProcedureCode, ProcedureTranslator, response_to_dict


DB_PATH = ROOT / "data" / "processed" / "healthscan.sqlite"
QUALITY_SUPPRESS = {"low_outlier", "placeholder_amount"}
HEADLINE_PRICE_TYPES = {"cash", "negotiated", "negotiated_min"}

KNOWN_LOCATIONS = {
    "90095": (34.0664, -118.4452, "Los Angeles, CA 90095"),
    "90033": (34.0500, -118.2059, "Los Angeles, CA 90033"),
    "90089": (34.0224, -118.2851, "Los Angeles, CA 90089"),
    "92037": (32.8328, -117.2713, "La Jolla, CA 92037"),
    "92103": (32.7498, -117.1670, "San Diego, CA 92103"),
    "92123": (32.8103, -117.1324, "San Diego, CA 92123"),
    "91910": (32.6401, -117.0842, "Chula Vista, CA 91910"),
    "los angeles": (34.0522, -118.2437, "Los Angeles, CA"),
    "los angeles ca": (34.0522, -118.2437, "Los Angeles, CA"),
    "la": (34.0522, -118.2437, "Los Angeles, CA"),
    "san diego": (32.7157, -117.1611, "San Diego, CA"),
    "san diego ca": (32.7157, -117.1611, "San Diego, CA"),
    "chula vista": (32.6401, -117.0842, "Chula Vista, CA"),
    "chula vista ca": (32.6401, -117.0842, "Chula Vista, CA"),
    "91911": (32.6180, -117.0347, "Chula Vista, CA 91911"),
    "san francisco": (37.7749, -122.4194, "San Francisco, CA"),
    "san francisco ca": (37.7749, -122.4194, "San Francisco, CA"),
    "94102": (37.7793, -122.4192, "San Francisco, CA 94102"),
}

HOSPITAL_COORDS = {
    "Ronald Reagan UCLA Medical Center": (34.0665, -118.4460),
    "Keck Hospital of USC": (34.0628, -118.2037),
    "Scripps Green Hospital": (32.8995, -117.2430),
    "UC San Diego Medical Center": (32.7549, -117.1658),
    "Rady Children's Hospital": (32.7984, -117.1511),
    "Sharp Chula Vista Medical Center": (32.6185, -117.0220),
    "Cedars-Sinai Medical Center": (34.0752, -118.3802),
    "Providence Saint John's Health Center": (34.0273, -118.4792),
    "Hoag Hospital Newport Beach": (33.6221, -117.9333),
    "Huntington Hospital": (34.1332, -118.1522),
    "Providence Cedars-Sinai Tarzana Medical Center": (34.1708, -118.5317),
    "Providence Holy Cross Medical Center": (34.2794, -118.4590),
    "Providence Saint Joseph Medical Center": (34.1578, -118.3273),
    "Hollywood Presbyterian Medical Center": (34.0963, -118.2901),
    "UCI Medical Center": (33.7874, -117.8866),
    "MemorialCare Orange Coast Medical Center": (33.7011, -117.9563),
    "Loma Linda University Medical Center": (34.0491, -117.2634),
    "Riverside Community Hospital": (33.9765, -117.3826),
    "Tri-City Medical Center": (33.1857, -117.2908),
    "Los Robles Regional Medical Center": (34.2078, -118.8831),
    "Community Memorial Healthcare - Ventura": (34.2740, -119.2582),
}

HOSPITAL_METADATA = {
    "Rady Children's Hospital": {
        "address": "3020 Children's Way, San Diego, CA 92123",
        "state": "CA",
        "zip": "92123",
    },
    "Cedars-Sinai Medical Center": {
        "address": "8700 Beverly Blvd, Los Angeles, CA 90048",
        "state": "CA",
        "zip": "90048",
    },
    "Hollywood Presbyterian Medical Center": {
        "address": "1300 N Vermont Ave, Los Angeles, CA 90027",
        "state": "CA",
        "zip": "90027",
    },
    "Huntington Hospital": {
        "address": "100 W California Blvd, Pasadena, CA 91105",
        "state": "CA",
        "zip": "91105",
    },
    "UCI Medical Center": {
        "address": "101 The City Drive South, Orange, CA 92868",
        "state": "CA",
        "zip": "92868",
    },
    "Hoag Hospital Newport Beach": {
        "address": "One Hoag Drive, Newport Beach, CA 92663",
        "state": "CA",
        "zip": "92663",
    },
    "MemorialCare Orange Coast Medical Center": {
        "address": "9920 Talbert Avenue, Fountain Valley, CA 92708",
        "state": "CA",
        "zip": "92708",
    },
    "Loma Linda University Medical Center": {
        "address": "11234 Anderson Street, Loma Linda, CA 92354",
        "state": "CA",
        "zip": "92354",
    },
    "Riverside Community Hospital": {
        "address": "4445 Magnolia Avenue, Riverside, CA 92501",
        "state": "CA",
        "zip": "92501",
    },
    "Tri-City Medical Center": {
        "address": "4002 Vista Way, Oceanside, CA 92056",
        "state": "CA",
        "zip": "92056",
    },
    "Los Robles Regional Medical Center": {
        "address": "215 West Janss Road, Thousand Oaks, CA 91360",
        "state": "CA",
        "zip": "91360",
    },
    "Community Memorial Healthcare - Ventura": {
        "address": "147 N Brent Street, Ventura, CA 93003",
        "state": "CA",
        "zip": "93003",
    },
}

SUPPORTED_EXAMPLES = [
    "colonoscopy",
    "MRI brain",
    "cataract surgery",
    "hip replacement",
    "mammogram",
    "cardiac catheterization",
]


@dataclass(frozen=True)
class Location:
    lat: float
    lng: float
    label: str
    source: str


def normalize_location(value: str) -> str:
    return " ".join(value.lower().replace(",", " ").split())


def geocode(value: str) -> Location | None:
    text = value.strip()
    if not text:
        return None
    normalized = normalize_location(text)
    if normalized in KNOWN_LOCATIONS:
        lat, lng, label = KNOWN_LOCATIONS[normalized]
        return Location(lat, lng, label, "local")
    digits = "".join(ch for ch in normalized if ch.isdigit())
    if len(digits) == 5 and digits in KNOWN_LOCATIONS:
        lat, lng, label = KNOWN_LOCATIONS[digits]
        return Location(lat, lng, label, "local")

    query = urllib.parse.urlencode({"q": text, "format": "json", "limit": "1", "countrycodes": "us"})
    request = urllib.request.Request(
        f"https://nominatim.openstreetmap.org/search?{query}",
        headers={"User-Agent": "HealthScan local MVP"},
    )
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return None
    if not payload:
        return None
    first = payload[0]
    return Location(float(first["lat"]), float(first["lon"]), first.get("display_name", text), "nominatim")


def miles_between(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius = 3958.8
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return radius * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


def row_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def code_from_payload(payload: dict[str, Any]) -> list[ProcedureCode] | None:
    selected = payload.get("selected")
    if not selected:
        return None
    return [
        ProcedureCode(
            procedure_code=str(selected["procedure_code"]),
            code_type=str(selected["code_type"]).upper(),
            description=str(selected.get("label") or selected.get("plain_name") or payload.get("procedure") or "Selected procedure"),
            setting=str(selected.get("setting") or "unknown"),  # type: ignore[arg-type]
            is_primary=True,
        )
    ]


def translate(payload: dict[str, Any]) -> tuple[dict[str, Any], list[ProcedureCode]]:
    selected_codes = code_from_payload(payload)
    if selected_codes:
        return (
            {
                "status": "match",
                "source": "selection",
                "candidates": [
                    {
                        "description": selected_codes[0].description,
                        "confidence": 1,
                        "codes": [asdict(code) for code in selected_codes],
                    }
                ],
            },
            selected_codes,
        )

    translator = ProcedureTranslator()
    response = translator.translate(str(payload.get("procedure") or ""))
    translation = response_to_dict(response)
    if response.status != "match":
        return translation, []
    codes = list(response.candidates[0].codes) if response.candidates else []
    return translation, codes


def query_rows(connection: sqlite3.Connection, codes: list[ProcedureCode]) -> list[dict[str, Any]]:
    if not codes:
        return []
    clauses = []
    params: list[str] = []
    for code in codes:
        clauses.append("(UPPER(p.code_type) = ? AND p.procedure_code = ?)")
        params.extend([code.code_type.upper(), code.procedure_code])

    rows = connection.execute(
        f"""
        SELECT
            p.hospital_id,
            h.name AS hospital_name,
            h.address,
            h.state,
            h.zip,
            p.procedure_name,
            p.procedure_code,
            p.code_type,
            p.description,
            p.setting,
            p.price_type,
            p.amount,
            p.payer_name,
            p.plan_name,
            p.last_updated,
            p.source_url,
            COALESCE(p.data_quality_flag, p.user_relevance_flag, 'ok') AS data_quality_flag,
            p.parsed_at
        FROM indexed_prices p
        JOIN hospitals h ON h.id = p.hospital_id
        WHERE {" OR ".join(clauses)}
        ORDER BY p.hospital_id, p.amount
        """,
        params,
    ).fetchall()
    return [row_dict(row) for row in rows]


def price_allowed(row: dict[str, Any], price_filter: str) -> bool:
    price_type = row["price_type"]
    if row.get("data_quality_flag") in QUALITY_SUPPRESS:
        return False
    if price_type not in HEADLINE_PRICE_TYPES:
        return False
    if price_filter == "cash":
        return price_type == "cash"
    if price_filter == "negotiated":
        return price_type in {"negotiated", "negotiated_min"}
    return True


def price_rank(price_type: str) -> int:
    return {"cash": 0, "negotiated": 1, "negotiated_min": 2}.get(price_type, 99)


def display_payer_plan(row: dict[str, Any]) -> str:
    parts = [row.get("payer_name"), row.get("plan_name")]
    text = " / ".join(str(part) for part in parts if part)
    if row.get("price_type") == "cash":
        return f"Source file field: {text}" if text else "Cash / self-pay"
    if not text:
        return "Not listed"
    return text


def source_metadata(row: dict[str, Any]) -> dict[str, Any]:
    hospital_file_date = row.get("last_updated")
    indexed_at = row.get("parsed_at")
    return {
        "url": row.get("source_url"),
        "hospital_file_date": hospital_file_date,
        "indexed_at": indexed_at,
        "timestamp_label": "Hospital file date" if hospital_file_date else "Indexed by HealthScan",
        "display_timestamp": hospital_file_date or indexed_at,
    }


def price_filter_label(price_filter: str) -> str:
    if price_filter == "cash":
        return "Self-pay prices"
    if price_filter == "negotiated":
        return "Insurance negotiated rates"
    return "All prices — advanced"


def price_selection_explanation(price_filter: str, insurance_filter: str = "all") -> str:
    if price_filter == "cash":
        text = "Showing self-pay prices first. Have insurance? Select your insurer to compare payer-specific negotiated rates."
    elif price_filter == "negotiated":
        text = "Showing insurance negotiated rates. These are payer/plan-specific hospital-published rates, not final out-of-pocket costs."
    else:
        text = "Advanced view: this mixes self-pay prices and payer-specific negotiated rates, so the lowest and highest prices may not be comparable."
    if insurance_filter and insurance_filter != "all":
        text += f" Applied insurance filter: {insurance_filter}."
    return text


def normalize_filter_text(value: Any) -> str:
    return " ".join(str(value or "").lower().split())


def canonical_payer_name(value: Any) -> str:
    text = str(value or "").strip()
    normalized = normalize_filter_text(text)
    compact = normalized.replace("[", " ").replace("]", " ")
    if "blue shield" in compact:
        return "Blue Shield"
    if "blue cross" in compact or "anthem" in compact:
        return "Anthem Blue Cross" if "anthem" in compact else "Blue Cross"
    if "aetna" in compact:
        return "Aetna"
    if "cigna" in compact:
        return "Cigna"
    if "united" in compact or "uhc" in compact:
        return "UnitedHealthcare"
    if "kaiser" in compact:
        return "Kaiser Permanente"
    if "medicare" in compact:
        return "Medicare"
    if "medi-cal" in compact or "medicaid" in compact:
        return "Medi-Cal / Medicaid"
    return text


def insurance_matches(row: dict[str, Any], insurance_filter: str) -> bool:
    if not insurance_filter or insurance_filter == "all":
        return True
    needle = normalize_filter_text(insurance_filter)
    payer = normalize_filter_text(row.get("payer_name"))
    canonical_payer = normalize_filter_text(canonical_payer_name(row.get("payer_name")))
    plan = normalize_filter_text(row.get("plan_name"))
    display = normalize_filter_text(display_payer_plan(row))
    return needle in {payer, canonical_payer, display} or needle in payer or needle in plan or needle in display


COMMON_PAYER_ORDER = {
    "Aetna": 0,
    "Anthem Blue Cross": 1,
    "Blue Cross": 2,
    "Blue Shield": 3,
    "Cigna": 4,
    "UnitedHealthcare": 5,
    "Kaiser Permanente": 6,
    "Medicare": 7,
    "Medi-Cal / Medicaid": 8,
}


def insurance_filter_options(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for row in rows:
        payer = canonical_payer_name(row.get("payer_name"))
        if not payer or row.get("price_type") == "cash":
            continue
        counts[payer] = counts.get(payer, 0) + 1
    return [
        {"value": payer, "label": payer, "count": count}
        for payer, count in sorted(
            counts.items(),
            key=lambda item: (COMMON_PAYER_ORDER.get(item[0], 999), item[0].lower()),
        )
    ]


def price_details_help_text() -> str:
    return (
        "Hospitals can publish the same dollar amount for different payer or plan contracts. "
        "HealthScan keeps those rows when the payer/plan differs, because they are distinct negotiated rates, "
        "but removes exact duplicate rows with the same type, amount, payer, and plan."
    )


def unavailable_message() -> str:
    return (
        "HealthScan recognized this procedure, but this alpha has no indexed price rows for it yet. "
        "This usually means coverage is still incomplete, not broken. Try one of the supported examples or a nearby Southern California hospital market."
    )


def no_results_message() -> str:
    return (
        "Indexed prices exist for this procedure, but none matched the current location, radius, and price filter. "
        "Expand the radius, switch Price type to All actionable, or try one of the selected Southern California hospitals."
    )


def user_testing_prompts() -> list[str]:
    return [
        "What did you think HealthScan was telling you?",
        "Did you trust the prices and source information shown? Why or why not?",
        "Was any price label, payer/plan text, or repeated-price note confusing?",
        "Could you find the hospital source/date information for a result?",
        "What would stop you from using this before scheduling care?",
        "What procedure and location did you search?",
    ]


def display_amount_bucket(row: dict[str, Any]) -> tuple[str, int]:
    amount = float(row["amount"])
    return (str(row["price_type"]), int(amount + 0.5))


def exact_price_identity(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        row.get("price_type"),
        round(float(row["amount"]), 2),
        row.get("payer_name") or "",
        row.get("plan_name") or "",
        row.get("source_url") or "",
    )


def dedupe_exact_price_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    deduped: list[dict[str, Any]] = []
    for row in rows:
        identity = exact_price_identity(row)
        if identity in seen:
            continue
        seen.add(identity)
        deduped.append(row)
    return deduped


def summarize_payer_plans(rows: list[dict[str, Any]]) -> str:
    labels = [display_payer_plan(row) for row in rows]
    listed = [label for label in labels if label != "Not listed"]
    if not listed:
        if len(rows) == 1:
            return "Not listed"
        return f"{len(rows)} source rows; payer/plan not listed"
    unique_labels = list(dict.fromkeys(listed))
    if len(unique_labels) == 1:
        return unique_labels[0]
    preview = "; ".join(unique_labels[:3])
    if len(unique_labels) > 3:
        preview += f"; +{len(unique_labels) - 3} more"
    return f"{len(unique_labels)} payer/plans: {preview}"


def serialize_price_group(rows: list[dict[str, Any]]) -> dict[str, Any]:
    first = rows[0]
    group_count = len(rows)
    note = None
    if group_count > 1:
        note = f"{group_count} distinct payer/plan rows share this same displayed amount."
    return {
        "type": first["price_type"],
        "amount": float(first["amount"]),
        "payer_name": first["payer_name"],
        "plan_name": first["plan_name"],
        "payer_plan_display": summarize_payer_plans(rows),
        "display_amount_group_count": group_count,
        "display_amount_note": note,
        "payer_plan_options": [display_payer_plan(row) for row in rows],
        "source": source_metadata(first),
        "last_updated": first["last_updated"] or first["parsed_at"],
        "quality": first.get("data_quality_flag") or "ok",
    }


def group_price_rows_by_display_amount(rows: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    groups: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(display_amount_bucket(row), []).append(row)
    return list(groups.values())


def build_hospitals(
    rows: list[dict[str, Any]],
    location: Location,
    radius: float,
    price_filter: str,
    sort: str,
    insurance_filter: str = "all",
) -> tuple[list[dict[str, Any]], int]:
    grouped: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(int(row["hospital_id"]), []).append(row)

    hospitals = []
    in_radius_count = 0
    for hospital_id, hospital_rows in grouped.items():
        first = hospital_rows[0]
        coords = HOSPITAL_COORDS.get(first["hospital_name"])
        if coords is None:
            zip_code = str(first.get("zip") or "")
            known = KNOWN_LOCATIONS.get(zip_code)
            coords = (known[0], known[1]) if known else None
        if coords is None:
            continue

        distance = miles_between(location.lat, location.lng, coords[0], coords[1])
        if distance <= radius:
            in_radius_count += 1
        else:
            continue

        eligible = [row for row in hospital_rows if price_allowed(row, price_filter) and insurance_matches(row, insurance_filter)]
        eligible.sort(key=lambda row: (price_rank(row["price_type"]), float(row["amount"])))
        eligible = dedupe_exact_price_rows(eligible)
        price_groups = group_price_rows_by_display_amount(eligible)
        headline = eligible[0] if eligible else None
        suppressed = [row for row in hospital_rows if row.get("data_quality_flag") in QUALITY_SUPPRESS]
        prices = [serialize_price_group(group) for group in price_groups[:8]]
        if headline is None:
            continue

        metadata = HOSPITAL_METADATA.get(first["hospital_name"], {})
        address = first["address"] or metadata.get("address")
        state = first.get("state") or metadata.get("state")
        zip_code = first.get("zip") or metadata.get("zip")

        hospitals.append(
            {
                "hospital_id": hospital_id,
                "name": first["hospital_name"],
                "address": address,
                "state": state,
                "zip": zip_code,
                "distance_miles": round(distance, 1),
                "procedure_name": headline["procedure_name"],
                "procedure_code": headline["procedure_code"],
                "code_type": headline["code_type"],
                "headline_price": {
                    "type": headline["price_type"],
                    "amount": float(headline["amount"]),
                    "payer_name": headline["payer_name"],
                    "plan_name": headline["plan_name"],
                    "payer_plan_display": display_payer_plan(headline),
                    "source": source_metadata(headline),
                    "last_updated": headline["last_updated"] or headline["parsed_at"],
                },
                "prices": prices,
                "suppressed_price_count": len(suppressed),
                "source_url": headline["source_url"],
                "selection_explanation": price_selection_explanation(price_filter, insurance_filter),
            }
        )

    if sort == "distance":
        hospitals.sort(key=lambda item: item["distance_miles"])
    else:
        hospitals.sort(key=lambda item: (item["headline_price"]["amount"], item["distance_miles"]))
    return hospitals, in_radius_count


def price_range_summary(hospitals: list[dict[str, Any]]) -> dict[str, dict[str, float | str]]:
    buckets = {
        "cash": {"label": "Self-pay range", "values": []},
        "negotiated": {"label": "Insurance negotiated range", "values": []},
    }
    for hospital in hospitals:
        headline = hospital.get("headline_price", {})
        price_type = headline.get("type")
        amount = headline.get("amount")
        if amount is None:
            continue
        if price_type == "cash":
            buckets["cash"]["values"].append(float(amount))
        elif price_type in {"negotiated", "negotiated_min"}:
            buckets["negotiated"]["values"].append(float(amount))

    summary: dict[str, dict[str, float | str]] = {}
    for key, bucket in buckets.items():
        values = bucket["values"]
        if not values:
            continue
        summary[key] = {"label": str(bucket["label"]), "min": min(values), "max": max(values)}
    return summary


def price_range_summary_for_rows(
    rows: list[dict[str, Any]],
    location: Location,
    radius: float,
    price_filter: str,
    insurance_filter: str = "all",
) -> dict[str, dict[str, float | str]]:
    filters = ["cash", "negotiated"] if price_filter == "all" else [price_filter]
    summary: dict[str, dict[str, float | str]] = {}
    for filter_name in filters:
        hospitals, _ = build_hospitals(rows, location, radius, filter_name, "price", insurance_filter)
        summary.update(price_range_summary(hospitals))
    return summary


def search(payload: dict[str, Any]) -> dict[str, Any]:
    location = geocode(str(payload.get("location") or ""))
    if location is None:
        return {
            "status": "location_not_found",
            "message": "Enter a Southern California ZIP code or city/state. Alpha coverage currently focuses on selected Southern California hospitals.",
            "examples": SUPPORTED_EXAMPLES,
        }

    translation, codes = translate(payload)
    if translation.get("status") in {"ambiguous", "clarify"}:
        return {"status": "clarification", "translation": translation, "location": asdict(location)}
    if translation.get("status") != "match":
        return {
            "status": "unavailable",
            "translation": translation,
            "location": asdict(location),
            "message": translation.get("message") or "That procedure is not available in the current index.",
            "examples": SUPPORTED_EXAMPLES,
            "testing_prompts": user_testing_prompts(),
        }

    radius = float(payload.get("radius") or 50)
    price_filter = str(payload.get("priceType") or "cash")
    insurance_filter = str(payload.get("insuranceFilter") or "all")
    sort = str(payload.get("sort") or "price")

    connection = sqlite3.connect(DEFAULT_DB_PATH if DEFAULT_DB_PATH.exists() else DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        rows = query_rows(connection, codes)
    finally:
        connection.close()

    if not rows:
        return {
            "status": "unavailable",
            "translation": translation,
            "location": asdict(location),
            "codes": [asdict(code) for code in codes],
            "message": unavailable_message(),
            "examples": SUPPORTED_EXAMPLES,
            "testing_prompts": user_testing_prompts(),
        }

    option_rows = [row for row in rows if price_allowed(row, price_filter)]
    insurance_filters = insurance_filter_options(option_rows)
    hospitals, in_radius_count = build_hospitals(rows, location, radius, price_filter, sort, insurance_filter)
    if not hospitals:
        return {
            "status": "no_results_near_location",
            "translation": translation,
            "location": asdict(location),
            "codes": [asdict(code) for code in codes],
            "total_indexed_hospitals": len({row["hospital_id"] for row in rows}),
            "hospitals_in_radius": in_radius_count,
            "radius": radius,
            "price_filter": price_filter,
            "price_filter_label": price_filter_label(price_filter),
            "insurance_filter": insurance_filter,
            "insurance_filters": insurance_filters,
            "message": no_results_message(),
            "examples": SUPPORTED_EXAMPLES,
            "testing_prompts": user_testing_prompts(),
        }

    return {
        "status": "limited_coverage" if len(hospitals) < 3 else "results",
        "translation": translation,
        "location": asdict(location),
        "codes": [asdict(code) for code in codes],
        "radius": radius,
        "price_filter": price_filter,
        "price_filter_label": price_filter_label(price_filter),
        "insurance_filter": insurance_filter,
        "insurance_filters": insurance_filters,
        "sort": sort,
        "hospitals": hospitals,
        "price_ranges": price_range_summary_for_rows(rows, location, radius, price_filter, insurance_filter),
        "total_indexed_hospitals": len({row["hospital_id"] for row in rows}),
        "price_details_help": price_details_help_text(),
        "testing_prompts": user_testing_prompts(),
    }


def main() -> None:
    payload = json.loads(sys.stdin.read() or "{}")
    print(json.dumps(search(payload)))


if __name__ == "__main__":
    main()
