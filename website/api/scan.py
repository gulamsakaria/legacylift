"""Vercel Python serverless function: /api/scan.

Runs the real LegacyLift pipeline (scan -> plan -> fix -> tests -> verify
-> report) against an uploaded PHP project and returns the generated
report.html directly as the response. This is the same engine the CLI
(`legacylift run`) and the local dashboard (`legacylift dashboard`, see
src/legacylift/webapp.py) use — vendored into _vendor/legacylift/ so this
function is self-contained (Vercel's Root Directory for this project is
`website/`, so the function can't reach the sibling src/legacylift/
package outside it; see _vendor/README.md).

Deliberately stateless: everything happens in one request/response inside
a temp directory that's deleted before the function returns. There is no
run history here (unlike the local dashboard) — Vercel serverless
functions don't share a persistent filesystem between invocations. Anyone
who wants history, larger uploads, or a migration-notes-driven run should
use `legacylift dashboard` locally (see the README).
"""

from __future__ import annotations

import base64
import html
import io
import shutil
import sys
import tempfile
import traceback
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "_vendor"))

from flask import Flask, request  # noqa: E402

from legacylift.config import load_config  # noqa: E402
from legacylift.fixer.engine import run_fixer  # noqa: E402
from legacylift.planner import build_plan, write_plan  # noqa: E402
from legacylift.report import write_all_reports  # noqa: E402
from legacylift.scanner.engine import scan_path  # noqa: E402
from legacylift.tests_gen import generate_tests  # noqa: E402
from legacylift.verifier import verify as run_verify  # noqa: E402

ALLOWED_SINGLE_FILE_EXT = {".php", ".phtml", ".inc"}
# Vercel Serverless Functions cap the request body around 4.5 MB on most
# plans — stay under that with headroom rather than let the platform 413.
MAX_UPLOAD_BYTES = 4 * 1024 * 1024

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES


class UploadError(ValueError):
    """A problem with the upload itself, not the scan pipeline."""


def _safe_extract_zip(zf: zipfile.ZipFile, dest: Path) -> None:
    dest = dest.resolve()
    for member in zf.infolist():
        target = (dest / member.filename).resolve()
        if target != dest and dest not in target.parents:
            raise UploadError(f"Unsafe path inside zip: {member.filename!r}")
    zf.extractall(dest)


def _single_project_dir(src_dir: Path) -> Path:
    entries = [e for e in src_dir.iterdir() if not e.name.startswith("__MACOSX")]
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]
    return src_dir


def _error_page(message: str) -> str:
    return f"""<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Scan failed — LegacyLift</title>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;
             max-width:640px;margin:80px auto;padding:0 20px;color:#1b1e23;">
<h2 style="margin-bottom:4px;">Scan failed</h2>
<pre style="white-space:pre-wrap;background:#fdecec;border:1px solid #d1273d;color:#7a1626;
            border-radius:10px;padding:16px;font-size:13px;">{html.escape(message)}</pre>
<p><a href="/" style="color:#2f6fed;font-weight:600;text-decoration:none;">&larr; Back to LegacyLift</a></p>
</body></html>"""


_BAR_BASE_STYLE = (
    "background:#2f6fed;color:#fff;padding:8px 16px;border-radius:8px;"
    "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;"
    "font-size:13px;font-weight:700;text-decoration:none;box-shadow:0 4px 10px rgba(0,0,0,.2);"
    "display:inline-block;"
)


def _zip_dir_to_data_uri(root: Path) -> str:
    """Zip an entire directory in memory and return it as a base64 data: URI
    — used so the "after" code can be downloaded straight from the report
    page with no second request (the live scan is stateless: the temp
    directory this reads from is deleted right after the response is built)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for fpath in sorted(root.rglob("*")):
            if fpath.is_file():
                zf.write(fpath, fpath.relative_to(root).as_posix())
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:application/zip;base64,{encoded}"


def _top_bar(modernized_zip_uri: str | None) -> str:
    download = ""
    if modernized_zip_uri:
        download = (
            f'<a href="{modernized_zip_uri}" download="legacylift-modernized.zip" '
            f'style="{_BAR_BASE_STYLE}background:#1f9d55;">&#11015; Download modernized code (.zip)</a>'
        )
    return (
        '<div style="position:sticky;top:0;z-index:9999;display:flex;gap:10px;flex-wrap:wrap;'
        'align-items:center;padding:10px 16px;background:rgba(15,17,22,.92);'
        'backdrop-filter:blur(6px);">'
        f'<a href="/" style="{_BAR_BASE_STYLE}">&larr; Scan another file</a>'
        f"{download}"
        "</div>"
    )


@app.route("/api/scan", methods=["POST"])
def scan():
    file = request.files.get("project")
    if file is None or file.filename == "":
        return _error_page("No file was uploaded."), 400

    work_dir = Path(tempfile.mkdtemp(prefix="legacylift_"))
    try:
        src_dir = work_dir / "src"
        out_dir = work_dir / "out"
        src_dir.mkdir(parents=True, exist_ok=True)

        filename = file.filename
        suffix = Path(filename).suffix.lower()

        if suffix == ".zip":
            tmp_zip = work_dir / "upload.zip"
            file.save(tmp_zip)
            with zipfile.ZipFile(tmp_zip) as zf:
                _safe_extract_zip(zf, src_dir)
            scan_root = _single_project_dir(src_dir)
        elif suffix in ALLOWED_SINGLE_FILE_EXT:
            file.save(src_dir / filename)
            scan_root = src_dir
        else:
            return _error_page(
                f"Unsupported file type '{suffix or filename}'. "
                "Upload a .zip of your PHP project, or a single .php file."
            ), 400

        cfg = load_config(scan_root)
        before_scan = scan_path(scan_root, cfg)
        if before_scan.files_scanned == 0:
            return _error_page(
                "No .php files found in the upload. Zip your project's source "
                "folder (or upload a single .php file) and try again."
            ), 400

        plan = build_plan(before_scan)
        write_plan(plan, out_dir)

        fix_result = run_fixer(scan_root, cfg, out_dir, apply=True)
        generate_tests(before_scan, scan_root, out_dir / "tests_generated")
        verify_result = run_verify(before_scan, fix_result.modernized_root, cfg)
        write_all_reports(before_scan, plan, fix_result, verify_result, out_dir)

        # Build the "after" download before the temp dir is wiped in `finally` —
        # the live scan is stateless (no second request could fetch it later),
        # so it travels home embedded in this same response as a data: URI.
        modernized_zip_uri = None
        changed = sum(1 for f in fix_result.files if f.changed)
        if changed and fix_result.modernized_root is not None:
            modernized_zip_uri = _zip_dir_to_data_uri(fix_result.modernized_root)

        report_html = (out_dir / "report.html").read_text(encoding="utf-8")
        report_html = report_html.replace("<body>", "<body>" + _top_bar(modernized_zip_uri), 1)
        return report_html, 200, {"Content-Type": "text/html; charset=utf-8"}

    except (UploadError, zipfile.BadZipFile) as exc:
        return _error_page(str(exc)), 400
    except Exception:
        return _error_page("Scan failed:\n" + traceback.format_exc()), 500
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
