from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from frontend_server import no_cache_headers


def test_static_assets_are_served_with_no_cache_headers() -> None:
    headers = no_cache_headers()

    assert headers["Cache-Control"] == "no-store, no-cache, must-revalidate, max-age=0"
    assert headers["Pragma"] == "no-cache"
    assert headers["Expires"] == "0"
