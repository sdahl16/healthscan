from __future__ import annotations

import json
import csv
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

from frontend_search import search


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
PROCEDURE_MAPPING = ROOT / "data" / "reference" / "procedure_mapping.csv"
PORT = int(os.environ.get("PORT", "4173"))


def no_cache_headers() -> dict[str, str]:
    return {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
    }


class HealthScanHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/api/health":
            self.send_json(200, {"ok": True})
            return
        if self.path == "/api/procedures":
            self.send_json(200, load_procedures())
            return
        if self.path == "/api/locations":
            self.send_json(200, load_locations())
            return
        self.serve_static()

    def do_POST(self) -> None:
        if self.path != "/api/search":
            self.send_json(404, {"status": "error", "message": "Not found"})
            return
        try:
            length = int(self.headers.get("content-length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            self.send_json(200, search(payload))
        except Exception as error:
            self.send_json(500, {"status": "error", "message": str(error)})

    def serve_static(self) -> None:
        requested = unquote(self.path.split("?", 1)[0])
        if requested == "/":
            requested = "/index.html"
        path = (PUBLIC / requested.lstrip("/")).resolve()
        if PUBLIC.resolve() not in path.parents and path != PUBLIC.resolve():
            self.send_error(403)
            return
        if not path.exists() or not path.is_file():
            self.send_error(404)
            return
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(data)))
        for name, value in no_cache_headers().items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, status_code: int, payload: dict) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(data)))
        for name, value in no_cache_headers().items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    server = ThreadingHTTPServer(("localhost", PORT), HealthScanHandler)
    print(f"HealthScan frontend running at http://localhost:{PORT}")
    server.serve_forever()


def load_procedures() -> list[dict[str, str]]:
    with PROCEDURE_MAPPING.open(newline="", encoding="utf-8") as handle:
        rows = [
            {
                "plain_name": row["plain_name"],
                "procedure_code": row["primary_code"],
                "code_type": row["primary_code_type"],
            }
            for row in csv.DictReader(handle)
            if row.get("plain_name") and row.get("primary_code") and row.get("primary_code_type")
        ]
    return sorted(rows, key=lambda row: row["plain_name"].lower())


def load_locations() -> list[dict[str, str]]:
    return [
        {"value": "Los Angeles, CA", "label": "City"},
        {"value": "San Diego, CA", "label": "City"},
        {"value": "Chula Vista, CA", "label": "City"},
        {"value": "La Jolla, CA 92037", "label": "Scripps Green area"},
        {"value": "Los Angeles, CA 90033", "label": "Keck USC area"},
        {"value": "Los Angeles, CA 90089", "label": "USC area"},
        {"value": "Los Angeles, CA 90095", "label": "UCLA area"},
        {"value": "San Diego, CA 92103", "label": "UCSD Hillcrest area"},
        {"value": "San Diego, CA 92123", "label": "Rady area"},
        {"value": "Chula Vista, CA 91910", "label": "Chula Vista area"},
        {"value": "Chula Vista, CA 91911", "label": "Sharp Chula Vista area"},
        {"value": "San Francisco, CA", "label": "Out-of-area test"},
        {"value": "San Francisco, CA 94102", "label": "Out-of-area test"},
    ]


if __name__ == "__main__":
    main()
