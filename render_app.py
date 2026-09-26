"""Render.com entry point for the LegacyLift dashboard.

Render tells a web service which port to listen on through the ``PORT``
environment variable and only routes traffic to processes bound to
``0.0.0.0`` (not ``127.0.0.1``). The local ``legacylift dashboard`` command
defaults to ``127.0.0.1:8788``, so this tiny wrapper reads ``PORT`` in
Python -- not via shell ``$PORT`` substitution in the start command -- and
hands the real work to ``legacylift.webapp.main``.

Usage on Render:   python render_app.py
Local smoke test:  PORT=10000 python render_app.py

Environment variables (all optional):
    PORT                  Port to bind. Render sets this itself. Default 10000
                          (Render's own default), used if unset or invalid.
    LEGACYLIFT_DATA_DIR   Where run history and uploads are stored. Default
                          ``legacylift_dashboard_data`` in the working dir.
                          On Render's free tier this disk is ephemeral.

This file is deployment plumbing only; it does not change any scanning,
fixing or report logic.
"""

from __future__ import annotations

import os
import sys

DEFAULT_PORT = 10000
HOST = "0.0.0.0"  # required by Render; 127.0.0.1 is unreachable from outside


def resolve_port(environ: "os._Environ[str] | dict[str, str] | None" = None) -> int:
    """Return the port from ``PORT``, falling back to ``DEFAULT_PORT``.

    A missing, empty, non-numeric or out-of-range value falls back to the
    default with a warning on stderr, rather than crashing at boot.
    """
    env = os.environ if environ is None else environ
    raw = (env.get("PORT") or "").strip()
    if not raw:
        return DEFAULT_PORT
    try:
        port = int(raw)
    except ValueError:
        port = -1
    if not 1 <= port <= 65535:
        print(
            f"render_app: ignoring invalid PORT={raw!r}, using {DEFAULT_PORT}",
            file=sys.stderr,
        )
        return DEFAULT_PORT
    return port


def run() -> None:
    from legacylift.webapp import main

    data_dir = os.environ.get("LEGACYLIFT_DATA_DIR") or "legacylift_dashboard_data"
    main(host=HOST, port=resolve_port(), data_dir=data_dir)


if __name__ == "__main__":
    run()
