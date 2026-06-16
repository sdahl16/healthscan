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
    "Hoag Hospital Newport Beach": (33.6253, -117.9304),
    "Huntington Hospital": (34.1348, -118.1522),
    "Providence Cedars-Sinai Tarzana Medical Center": (34.1708, -118.5317),
    "Providence Holy Cross Medical Center": (34.2794, -118.4590),
    "Providence Saint Joseph Medical Center": (34.1578, -118.3273),
}

HOSPITAL_METADATA = {
    "Rady Children's Hospital": {
        "address": "3020 Children's Way, San Diego, CA 92123",
        "state": "CA",
        "zip": "92123",
    }
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
    if not text:
        return "Not listed"
    if row.get("price_type") == "cash":
        return f"Source file field: {text}"
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


def price_selection_explanation(price_filter: str) -> str:
    if price_filter == "cash":
        return "Showing the lowest eligible cash/self-pay row after suppressing flagged outliers."
    if price_filter == "negotiated":
        return "Showing the lowest eligible negotiated row after suppressing flagged outliers."
    return "Showing the lowest eligible actionable row, preferring cash/self-pay rows before negotiated rows and suppressing flagged outliers."


def build_hospitals(
    rows: list[dict[str, Any]],
    location: Location,
    radius: float,
    price_filter: str,
    sort: str,
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

        eligible = [row for row in hospital_rows if price_allowed(row, price_filter)]
        eligible.sort(key=lambda row: (price_rank(row["price_type"]), float(row["amount"])))
        headline = eligible[0] if eligible else None
        suppressed = [row for row in hospital_rows if row.get("data_quality_flag") in QUALITY_SUPPRESS]
        prices = [
            {
                "type": row["price_type"],
                "amount": float(row["amount"]),
                "payer_name": row["payer_name"],
                "plan_name": row["plan_name"],
                "payer_plan_display": display_payer_plan(row),
                "source": source_metadata(row),
                "last_updated": row["last_updated"] or row["parsed_at"],
                "quality": row.get("data_quality_flag") or "ok",
            }
            for row in eligible[:8]
        ]
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
                "selection_explanation": price_selection_explanation(price_filter),
            }
        )

    if sort == "distance":
        hospitals.sort(key=lambda item: item["distance_miles"])
    else:
        hospitals.sort(key=lambda item: (item["headline_price"]["amount"], item["distance_miles"]))
    return hospitals, in_radius_count


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
        }

    radius = float(payload.get("radius") or 50)
    price_filter = str(payload.get("priceType") or "all")
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
            "message": "HealthScan recognizes this procedure, but this alpha has no indexed price rows for it yet.",
            "examples": SUPPORTED_EXAMPLES,
        }

    hospitals, in_radius_count = build_hospitals(rows, location, radius, price_filter, sort)
    if not hospitals:
        return {
            "status": "no_results_near_location",
            "translation": translation,
            "location": asdict(location),
            "codes": [asdict(code) for code in codes],
            "total_indexed_hospitals": len({row["hospital_id"] for row in rows}),
            "hospitals_in_radius": in_radius_count,
            "radius": radius,
            "message": "Indexed prices exist for this procedure, but none matched the current location, radius, and price filter. Alpha coverage currently focuses on selected Southern California hospitals.",
            "examples": SUPPORTED_EXAMPLES,
        }

    return {
        "status": "limited_coverage" if len(hospitals) < 3 else "results",
        "translation": translation,
        "location": asdict(location),
        "codes": [asdict(code) for code in codes],
        "radius": radius,
        "price_filter": price_filter,
        "sort": sort,
        "hospitals": hospitals,
        "total_indexed_hospitals": len({row["hospital_id"] for row in rows}),
    }


def main() -> None:
    payload = json.loads(sys.stdin.read() or "{}")
    print(json.dumps(search(payload)))


if __name__ == "__main__":
    main()
