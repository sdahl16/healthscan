from __future__ import annotations

import csv
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "research" / "sandiego_mrf_discovery_phase1.csv"

TARGETS = [
    {"hospital_name": "Scripps Memorial Hospital La Jolla", "hospital_system": "Scripps Health", "domain": "scripps.org", "city": "La Jolla, CA"},
    {"hospital_name": "Scripps Mercy Hospital San Diego", "hospital_system": "Scripps Health", "domain": "scripps.org", "city": "San Diego, CA"},
    {"hospital_name": "Sharp Memorial Hospital", "hospital_system": "Sharp HealthCare", "domain": "sharp.com", "city": "San Diego, CA"},
    {"hospital_name": "Sharp Grossmont Hospital", "hospital_system": "Sharp HealthCare", "domain": "sharp.com", "city": "La Mesa, CA"},
    {"hospital_name": "Palomar Medical Center Escondido", "hospital_system": "Palomar Health", "domain": "palomarhealth.org", "city": "Escondido, CA"},
    {"hospital_name": "Kaiser Permanente San Diego Medical Center", "hospital_system": "Kaiser Permanente Southern California", "domain": "kaiserpermanente.org", "city": "San Diego, CA"},
    {"hospital_name": "Alvarado Hospital Medical Center", "hospital_system": "Prime Healthcare", "domain": "alvaradohospital.com", "city": "San Diego, CA"},
    {"hospital_name": "Paradise Valley Hospital", "hospital_system": "Prime Healthcare", "domain": "paradisevalleyhospital.net", "city": "National City, CA"},
]

CANDIDATE_PATHS = ["/cms-hpt.txt", "/price-transparency", "/price-transparency/", "/patients-visitors/billing/price-transparency"]
URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.I)
MRF_RE = re.compile(r"(?:standardcharges|standard-charges|standard_charges|machine.readable|mrf|price.transparency).*(?:\.csv|\.json|\.zip|/charges/export|download\.aspx)", re.I)


def fetch(url: str, *, max_bytes: int = 1_000_000) -> tuple[int | None, str | None, bytes, str | None]:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 HealthScan MRF discovery"})
    try:
        with urllib.request.urlopen(req, timeout=20, context=ssl.create_default_context()) as resp:
            return resp.status, resp.headers.get("content-type"), resp.read(max_bytes), None
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("content-type"), e.read(4096), str(e)
    except Exception as e:
        return None, None, b"", repr(e)


def probe_url(url: str) -> tuple[int | None, str | None, int, str | None]:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 HealthScan MRF discovery", "Range": "bytes=0-4095"})
    try:
        with urllib.request.urlopen(req, timeout=20, context=ssl.create_default_context()) as resp:
            sample = resp.read(4096)
            return resp.status, resp.headers.get("content-type"), len(sample), None
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("content-type"), 0, str(e)
    except Exception as e:
        return None, None, 0, repr(e)


def candidate_pages(domain: str) -> list[str]:
    roots = [f"https://{domain}", f"https://www.{domain}"] if not domain.startswith("www.") else [f"https://{domain}"]
    return [root + path for root in roots for path in CANDIDATE_PATHS]


def extract_links(page_url: str, body: bytes) -> list[str]:
    text = body.decode("utf-8", errors="ignore")
    urls = URL_RE.findall(text)
    rels = re.findall(r"(?:href|src)=['\"]([^'\"]+)['\"]", text, flags=re.I)
    urls.extend(urllib.parse.urljoin(page_url, rel) for rel in rels)
    cleaned = []
    for url in urls:
        url = url.strip().rstrip(",.;)")
        if MRF_RE.search(url) or url.endswith("cms-hpt.txt"):
            cleaned.append(url)
    return list(dict.fromkeys(cleaned))


def main() -> int:
    rows = []
    for target in TARGETS:
        print(f"discovering {target['hospital_name']}", flush=True)
        found = []
        page_notes = []
        for page in candidate_pages(target["domain"]):
            status, ctype, body, error = fetch(page)
            page_notes.append(f"{page}={status or error}")
            if status and status < 400 and body:
                for link in extract_links(page, body):
                    if link not in found:
                        found.append(link)
        if not found:
            rows.append({**target, "source_url": "", "mrf_url": "", "mrf_status": "", "mrf_content_type": "", "sample_bytes": "0", "status": "pending", "notes": "; ".join(page_notes)})
            continue
        for link in found:
            m_status, m_type, sample_bytes, m_error = probe_url(link)
            rows.append({**target, "source_url": link if link.endswith("cms-hpt.txt") else "", "mrf_url": link, "mrf_status": str(m_status or ""), "mrf_content_type": m_type or "", "sample_bytes": str(sample_bytes), "status": "verified" if m_status in {200, 206} else "candidate", "notes": m_error or "; ".join(page_notes)})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = ["hospital_name", "hospital_system", "city", "domain", "source_url", "mrf_url", "mrf_status", "mrf_content_type", "sample_bytes", "status", "notes"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote={OUT}")
    print(f"rows={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
