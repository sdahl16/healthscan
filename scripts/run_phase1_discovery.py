from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from healthscan.discovery import discover_first_available, likely_mrf_links, probe_url


ROOT = Path(__file__).resolve().parents[1]
TARGETS_PATH = ROOT / "data" / "reference" / "hospital_targets.csv"
LOG_PATH = ROOT / "data" / "research" / "phase1_discovery_log.csv"


def classify_format(url: str, content_type: str) -> str:
    lowered = f"{url} {content_type}".lower()
    if ".json" in lowered or "json" in lowered:
        return "JSON"
    if ".csv" in lowered or "csv" in lowered:
        return "CSV"
    if ".zip" in lowered or "zip" in lowered:
        return "ZIP"
    if ".gz" in lowered or "gzip" in lowered:
        return "GZIP"
    return "unknown"


def main() -> None:
    rows: list[dict[str, str]] = []
    with TARGETS_PATH.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["phase"] == "1":
                rows.append(row)

    fieldnames = [
        "checked_at",
        "hospital_system",
        "domain",
        "cms_hpt_url",
        "status",
        "mrf_url",
        "mrf_format",
        "file_size_bytes",
        "notes",
    ]

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()

        for target in rows:
            checked_at = datetime.now(timezone.utc).isoformat()
            try:
                discovery = discover_first_available(target["domain"])
                candidates = likely_mrf_links(discovery.links)
                mrf_url = candidates[0] if candidates else ""
                mrf_format = ""
                file_size = ""
                notes = f"found {len(discovery.links)} link(s); content_type={discovery.content_type}"

                if mrf_url:
                    probe = probe_url(mrf_url)
                    mrf_format = classify_format(probe.final_url, probe.content_type)
                    file_size = probe.content_length
                    notes = f"{notes}; probe_status={probe.status_code}; probe_content_type={probe.content_type}"

                writer.writerow(
                    {
                        "checked_at": checked_at,
                        "hospital_system": target["hospital_system"],
                        "domain": target["domain"],
                        "cms_hpt_url": discovery.source_url,
                        "status": "pass" if mrf_url else "no_mrf_link",
                        "mrf_url": mrf_url,
                        "mrf_format": mrf_format,
                        "file_size_bytes": file_size,
                        "notes": notes,
                    }
                )
            except Exception as error:  # noqa: BLE001 - this is a field research log.
                writer.writerow(
                    {
                        "checked_at": checked_at,
                        "hospital_system": target["hospital_system"],
                        "domain": target["domain"],
                        "cms_hpt_url": "",
                        "status": "fail",
                        "mrf_url": "",
                        "mrf_format": "",
                        "file_size_bytes": "",
                        "notes": f"{type(error).__name__}: {error}",
                    }
                )

    print(LOG_PATH)


if __name__ == "__main__":
    main()
