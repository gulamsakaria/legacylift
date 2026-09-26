"""Local dev-only server that mimics how Vercel will route this project:
static files served at "/", and api/scan.py's Flask app answering
POST /api/scan. Vercel does this routing itself in production — this
script exists only so the whole site (upload form included) can be
clicked through on localhost before deploying.

Usage:
    cd website
    python dev_server.py [port]   # default port 5500
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "api"))

from flask import send_from_directory  # noqa: E402

import scan  # website/api/scan.py — noqa: E402

ROOT = Path(__file__).resolve().parent


@scan.app.route("/", defaults={"path": "index.html"})
@scan.app.route("/<path:path>")
def _static(path: str):
    return send_from_directory(ROOT, path)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5500
    print(f"LegacyLift website (dev) running at http://127.0.0.1:{port}")
    scan.app.run(host="127.0.0.1", port=port)
