"""Upload dashboard: a small local web app so a real user can drop in their
own legacy PHP code (a .zip of a project, or a single .php file) and get a
real LegacyLift run — not the bundled demo. This is the same six-stage
pipeline `legacylift run` drives from the CLI (`cli.py::cmd_run`), just
wired to file uploads instead of a filesystem path, with each upload
getting its own run directory so multiple people/uploads don't collide.

Requires the `serve` extra: `pip install -e ".[serve]"`.
"""

from __future__ import annotations

import json
import shutil
import time
import traceback
import uuid
import zipfile
from pathlib import Path
from typing import Any

from .config import load_config
from .fixer.engine import run_fixer
from .planner import build_plan, write_plan
from .report import write_all_reports
from .scanner.engine import scan_path
from .tests_gen import generate_tests
from .verifier import verify as run_verify

ALLOWED_SINGLE_FILE_EXT = {".php", ".phtml", ".inc"}
MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB


class UploadError(ValueError):
    """A problem with the upload itself (bad zip, wrong type, too big) —
    distinct from a pipeline failure, so the dashboard can show a clear
    "fix your upload" message instead of a stack trace."""


def _safe_extract_zip(zf: zipfile.ZipFile, dest: Path) -> None:
    """Extract a zip while refusing entries that would escape ``dest``
    (a.k.a. zip-slip: ``../../etc/passwd``-style paths or absolute paths)."""
    dest = dest.resolve()
    for member in zf.infolist():
        target = (dest / member.filename).resolve()
        if target != dest and dest not in target.parents:
            raise UploadError(f"Unsafe path inside zip: {member.filename!r}")
    zf.extractall(dest)


def _single_project_dir(src_dir: Path) -> Path:
    """If the extracted zip is just one wrapper folder (the common case —
    GitHub's 'Download ZIP' does this), scan that folder directly instead
    of the wrapper, so paths in the report read naturally."""
    entries = [e for e in src_dir.iterdir() if not e.name.startswith("__MACOSX")]
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]
    return src_dir


def run_pipeline(source_root: Path, out_dir: Path, doc_path: Path | None = None) -> dict[str, Any]:
    """Run the full scan -> plan -> fix -> tests -> verify -> report pipeline
    against an uploaded project. Mirrors ``cli.py::cmd_run`` but returns a
    plain summary dict instead of printing to a terminal, so the dashboard
    can render it."""
    out_dir.mkdir(parents=True, exist_ok=True)

    if doc_path is not None and doc_path.exists():
        from .ingest import ingest as ingest_doc

        ingest_doc(doc_path, source_root)

    cfg = load_config(source_root)

    before_scan = scan_path(source_root, cfg)
    if before_scan.files_scanned == 0:
        raise UploadError(
            "No .php files found in the upload. Zip your project's source "
            "folder (or upload a single .php file) and try again."
        )

    plan = build_plan(before_scan)
    write_plan(plan, out_dir)

    fix_result = run_fixer(source_root, cfg, out_dir, apply=True)

    written = generate_tests(before_scan, source_root, out_dir / "tests_generated")

    verify_result = run_verify(before_scan, fix_result.modernized_root, cfg)

    write_all_reports(before_scan, plan, fix_result, verify_result, out_dir)

    changed = sum(1 for f in fix_result.files if f.changed)
    return {
        "risk_before": before_scan.project_risk_score,
        "risk_after": verify_result.after.project_risk_score,
        "findings_before": len(before_scan.findings),
        "findings_after": len(verify_result.after.findings),
        "critical_before": before_scan.findings_by_severity.get("critical", 0),
        "critical_after": verify_result.after.findings_by_severity.get("critical", 0),
        "files_scanned": before_scan.files_scanned,
        "files_changed": changed,
        "tests_generated": len(written),
        "verified": verify_result.passed,
    }


_PAGE_STYLE = """
  :root {
    --bg: #f7f7f9; --panel: #ffffff; --text: #1b1e23; --muted: #5b6270;
    --border: #e3e5e9; --accent: #2f6fed; --accent-dark: #2158c4; --accent2: #8a5cf6;
    --critical: #d1273d; --good: #1f9d55;
  }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#0f1116; --panel:#1a1d24; --text:#e7e9ee; --muted:#9aa2b1;
            --border:#2a2e38; --accent:#6f9bff; --accent-dark:#8fb0ff; --accent2:#a98bff; }
  }
  * { box-sizing: border-box; }
  html { background: var(--bg); }
  body { margin:0; background:var(--bg); color:var(--text); position:relative; min-height:100vh;
         font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;
         overflow-x:hidden; }

  /* --- floating gradient background --- */
  .bg-orbs { position:fixed; inset:0; overflow:hidden; z-index:0; pointer-events:none; }
  .orb { position:absolute; border-radius:50%; filter:blur(70px); opacity:.32; will-change:transform; }
  .orb1 { width:440px; height:440px; background:var(--accent); top:-140px; left:-120px;
          animation: float1 22s ease-in-out infinite; }
  .orb2 { width:360px; height:360px; background:var(--accent2); bottom:-120px; right:-100px;
          animation: float2 27s ease-in-out infinite; }
  .orb3 { width:260px; height:260px; background:var(--good); top:38%; left:62%;
          animation: float3 19s ease-in-out infinite; }
  @keyframes float1 { 0%,100% { transform:translate3d(0,0,0) scale(1); } 50% { transform:translate3d(60px,50px,0) scale(1.12); } }
  @keyframes float2 { 0%,100% { transform:translate3d(0,0,0) scale(1); } 50% { transform:translate3d(-50px,-40px,0) scale(1.08); } }
  @keyframes float3 { 0%,100% { transform:translate3d(0,0,0) scale(1); } 50% { transform:translate3d(-30px,36px,0) scale(0.92); } }

  header { position:relative; z-index:1; padding:30px 32px; border-bottom:1px solid var(--border); }
  .header-inner { max-width:840px; margin:0 auto; display:flex; align-items:center;
                  justify-content:space-between; gap:20px; }
  header h1 { margin:0 0 4px; font-size:24px; letter-spacing:-.01em; }
  .grad-text { background:linear-gradient(100deg, var(--accent), var(--accent2));
               -webkit-background-clip:text; background-clip:text; color:transparent; }
  header .sub { color:var(--muted); font-size:14px; max-width:52ch; }

  /* --- spinning radar mark --- */
  .radar { position:relative; width:56px; height:56px; border-radius:50%; flex:none;
           background:
             radial-gradient(circle, transparent 0 38%, var(--border) 39% 41%, transparent 42%),
             radial-gradient(circle, transparent 0 20%, var(--border) 21% 23%, transparent 24%);
           overflow:hidden; }
  .radar::after { content:""; position:absolute; inset:0; border-radius:50%;
           background:conic-gradient(from 0deg, rgba(111,155,255,.7), transparent 32%);
           animation: spin 2.6s linear infinite; }
  @keyframes spin { to { transform:rotate(360deg); } }

  main { position:relative; z-index:1; max-width:840px; margin:0 auto; padding:26px 20px 60px; }

  section { background:var(--panel); background:color-mix(in srgb, var(--panel) 86%, transparent);
            backdrop-filter:blur(14px); -webkit-backdrop-filter:blur(14px);
            border:1px solid var(--border); border-radius:16px;
            padding:22px 24px; margin-bottom:22px;
            box-shadow:0 14px 34px -22px rgba(0,0,0,.35); }
  section h2 { margin-top:0; font-size:16px; }

  .reveal { animation:reveal .55s cubic-bezier(.16,1,.3,1) both; }
  @keyframes reveal { from { opacity:0; transform:translateY(18px) rotateX(-6deg); } to { opacity:1; transform:none; } }

  .tilt { transition:transform .15s ease-out; will-change:transform; transform-style:preserve-3d; }

  label { display:block; font-size:13px; font-weight:600; margin:14px 0 6px; }
  input[type=file], input[type=text] { width:100%; padding:8px; border-radius:6px;
        border:1px solid var(--border); background:var(--bg); color:var(--text); font-size:13px; }
  .hint { color:var(--muted); font-size:12px; margin-top:4px; }

  /* --- drag & drop zone --- */
  .dropzone { position:relative; margin-top:10px; display:flex; flex-direction:column;
              align-items:center; justify-content:center; gap:6px; padding:34px 20px;
              border:2px dashed var(--border); border-radius:14px; cursor:pointer;
              text-align:center; transition:border-color .2s ease, background .2s ease, transform .15s ease; }
  .dropzone:hover, .dropzone.drag-over { border-color:var(--accent); transform:translateY(-2px);
              background:color-mix(in srgb, var(--accent) 8%, transparent); }
  .dropzone input[type=file] { position:absolute; inset:0; opacity:0; cursor:pointer; width:100%; height:100%; }
  .dz-icon { font-size:26px; }
  .dz-text { font-size:13px; font-weight:600; }

  button { margin-top:18px; padding:12px 26px; border:none; border-radius:10px;
           background:linear-gradient(135deg, var(--accent), var(--accent2)); color:#fff;
           font-size:14px; font-weight:700; cursor:pointer;
           box-shadow:0 8px 22px -8px rgba(47,111,237,.6);
           transition:transform .15s ease, box-shadow .15s ease, opacity .15s ease; }
  button:hover { transform:translateY(-2px); box-shadow:0 12px 28px -8px rgba(47,111,237,.7); }
  button:active { transform:translateY(0); }
  button:disabled { opacity:.6; cursor:progress; transform:none; }

  a { color:var(--accent); text-decoration:none; }
  a:hover { text-decoration:underline; }
  .empty { color:var(--muted); font-size:13px; }

  /* --- run cards --- */
  .run-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(230px,1fr)); gap:16px; }
  .run-card { background:var(--bg); border:1px solid var(--border); border-radius:14px; padding:16px;
              transition:transform .15s ease-out, box-shadow .15s ease-out; will-change:transform; }
  .run-card:hover { box-shadow:0 18px 34px -20px rgba(0,0,0,.4); }
  .run-name { font-weight:700; font-size:13px; margin-bottom:2px; word-break:break-all; }
  .run-time { color:var(--muted); font-size:11px; margin-bottom:14px; }
  .risk-row { display:flex; align-items:center; gap:8px; margin-bottom:7px; font-size:12px; }
  .risk-label { width:40px; flex:none; color:var(--muted); }
  .bar-track { position:relative; flex:1; height:8px; background:var(--border); border-radius:999px; overflow:hidden; }
  .bar { position:absolute; inset:0; width:0; border-radius:999px;
         transition:width 1.1s cubic-bezier(.16,1,.3,1); }
  .bar-before { background:linear-gradient(90deg, var(--critical), #ff8a65); }
  .bar-after { background:linear-gradient(90deg, var(--good), #6fe3a0); }
  .risk-num { width:24px; flex:none; text-align:right; font-weight:700; font-variant-numeric:tabular-nums; }
  .run-findings { color:var(--muted); font-size:12px; margin:10px 0 12px; }
  .open-btn { display:inline-block; font-size:12px; font-weight:700; }

  .error { position:relative; z-index:1; background:#fdecec; border:1px solid var(--critical); color:#7a1626;
           border-radius:12px; padding:14px 16px; white-space:pre-wrap; font-size:13px; margin-bottom:20px; }
  @media (prefers-color-scheme: dark) { .error { background:#301418; color:#ffb4bd; } }

  /* --- scanning overlay --- */
  .scan-overlay { position:fixed; inset:0; z-index:50; display:flex; align-items:center; justify-content:center;
                  background:rgba(10,12,16,.74); backdrop-filter:blur(6px); -webkit-backdrop-filter:blur(6px);
                  opacity:0; pointer-events:none; transition:opacity .25s ease; }
  .scan-overlay.show { opacity:1; pointer-events:all; }
  .scan-box { text-align:center; color:#fff; }
  .scan-ring { width:60px; height:60px; margin:0 auto 18px; border-radius:50%;
               border:3px solid rgba(255,255,255,.25); border-top-color:#8fb0ff;
               animation:spin .9s linear infinite; }
  .scan-text { font-size:14px; letter-spacing:.02em; }
"""

_PAGE_SCRIPT = """
(function () {
  // Real 3D tilt-on-hover for every card marked [data-tilt].
  document.querySelectorAll('[data-tilt]').forEach(function (card) {
    card.addEventListener('mousemove', function (e) {
      var r = card.getBoundingClientRect();
      var x = (e.clientX - r.left) / r.width - 0.5;
      var y = (e.clientY - r.top) / r.height - 0.5;
      card.style.transform = 'perspective(800px) rotateX(' + (-y * 7).toFixed(2) + 'deg) '
        + 'rotateY(' + (x * 7).toFixed(2) + 'deg) translateZ(4px)';
    });
    card.addEventListener('mouseleave', function () {
      card.style.transform = 'perspective(800px) rotateX(0deg) rotateY(0deg) translateZ(0px)';
    });
  });

  // Animate the risk bars and their numbers in from zero once the page has painted.
  function animateCount(el, target, duration) {
    var start = performance.now();
    function tick(now) {
      var p = Math.min(1, (now - start) / duration);
      var eased = 1 - Math.pow(1 - p, 3);
      el.textContent = Math.round(target * eased);
      if (p < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }
  requestAnimationFrame(function () {
    requestAnimationFrame(function () {
      document.querySelectorAll('.bar').forEach(function (bar) {
        bar.style.width = (bar.dataset.val || 0) + '%';
      });
      document.querySelectorAll('.count-up').forEach(function (el) {
        animateCount(el, parseInt(el.dataset.target || '0', 10), 900);
      });
    });
  });

  // Drag & drop wiring for the upload dropzone.
  var dz = document.getElementById('dropzone');
  var input = document.getElementById('project');
  var dzText = document.getElementById('dz-text');
  if (dz && input) {
    ['dragenter', 'dragover'].forEach(function (evt) {
      dz.addEventListener(evt, function (e) { e.preventDefault(); dz.classList.add('drag-over'); });
    });
    ['dragleave', 'drop'].forEach(function (evt) {
      dz.addEventListener(evt, function (e) { e.preventDefault(); dz.classList.remove('drag-over'); });
    });
    dz.addEventListener('drop', function (e) {
      if (e.dataTransfer && e.dataTransfer.files.length) {
        input.files = e.dataTransfer.files;
        dzText.textContent = e.dataTransfer.files[0].name;
      }
    });
    input.addEventListener('change', function () {
      if (input.files.length) dzText.textContent = input.files[0].name;
    });
  }

  // Perceived-progress overlay while the (synchronous) scan runs server-side.
  var form = document.getElementById('scan-form');
  var overlay = document.getElementById('scan-overlay');
  var stepText = document.getElementById('scan-step');
  var btn = document.getElementById('scan-btn');
  if (form && overlay) {
    form.addEventListener('submit', function () {
      if (!input || !input.files.length) return;
      if (btn) btn.disabled = true;
      overlay.classList.add('show');
      var steps = ['Uploading project…', 'Scanning for risk patterns…', 'Applying safe fixes…',
                   'Generating tests…', 'Verifying & building report…'];
      var i = 0;
      stepText.textContent = steps[0];
      setInterval(function () { i = (i + 1) % steps.length; stepText.textContent = steps[i]; }, 900);
    });
  }
})();
"""

_INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LegacyLift Dashboard</title>
<style>{{ style|safe }}</style></head>
<body>
<div class="bg-orbs" aria-hidden="true"><span class="orb orb1"></span><span class="orb orb2"></span><span class="orb orb3"></span></div>
<header class="reveal">
  <div class="header-inner">
    <div>
      <h1>LegacyLift <span class="grad-text">Dashboard</span></h1>
      <div class="sub">Upload your own legacy PHP project and get a real scan, fix and report — no demo data.</div>
    </div>
    <div class="radar" aria-hidden="true"></div>
  </div>
</header>
<main>
  {% if error %}<div class="error reveal">{{ error }}</div>{% endif %}

  <section class="tilt reveal" data-tilt>
    <h2>Scan a project</h2>
    <form id="scan-form" action="/upload" method="post" enctype="multipart/form-data">
      <label class="dropzone" id="dropzone" for="project">
        <input type="file" id="project" name="project" accept=".zip,.php,.phtml,.inc" required>
        <div class="dz-icon">⇪</div>
        <div class="dz-text" id="dz-text">Drop a .zip of your PHP project here, or click to browse</div>
        <div class="hint">A single .php file also works. Max 25&nbsp;MB.</div>
      </label>

      <label for="migration_notes">Migration notes (optional)</label>
      <input type="file" id="migration_notes" name="migration_notes" accept=".md,.txt">
      <div class="hint">A plain-English doc (target PHP version, do-not-touch paths) — parsed automatically, same as `legacylift ingest`.</div>

      <button type="submit" id="scan-btn">Run LegacyLift</button>
    </form>
  </section>

  <section class="reveal">
    <h2>Previous runs</h2>
    {% if runs %}
    <div class="run-grid">
      {% for r in runs %}
      <div class="run-card tilt" data-tilt>
        <div class="run-name">{{ r.name }}</div>
        <div class="run-time">{{ r.time }}</div>
        <div class="risk-row">
          <span class="risk-label">Before</span>
          <div class="bar-track"><div class="bar bar-before" data-val="{{ r.risk_before }}"></div></div>
          <span class="risk-num count-up" data-target="{{ r.risk_before }}">0</span>
        </div>
        <div class="risk-row">
          <span class="risk-label">After</span>
          <div class="bar-track"><div class="bar bar-after" data-val="{{ r.risk_after }}"></div></div>
          <span class="risk-num count-up" data-target="{{ r.risk_after }}">0</span>
        </div>
        <div class="run-findings">{{ r.findings_before }} &rarr; {{ r.findings_after }} findings</div>
        <a class="open-btn" href="/runs/{{ r.id }}/report.html">Open report &rarr;</a>
      </div>
      {% endfor %}
    </div>
    {% else %}
    <div class="empty">No runs yet — upload a project above.</div>
    {% endif %}
  </section>
</main>

<div class="scan-overlay" id="scan-overlay">
  <div class="scan-box">
    <div class="scan-ring"></div>
    <div class="scan-text" id="scan-step">Uploading…</div>
  </div>
</div>
<script>{{ script|safe }}</script>
</body></html>"""


def create_app(data_dir: Path):
    from flask import (
        Flask,
        abort,
        redirect,
        render_template_string,
        request,
        send_from_directory,
        url_for,
    )

    data_dir = Path(data_dir)
    runs_root = data_dir / "runs"
    runs_root.mkdir(parents=True, exist_ok=True)
    runs_index = data_dir / "runs.json"

    def _load_runs() -> list[dict[str, Any]]:
        if runs_index.exists():
            return json.loads(runs_index.read_text(encoding="utf-8"))
        return []

    def _save_runs(runs: list[dict[str, Any]]) -> None:
        runs_index.write_text(json.dumps(runs, indent=2), encoding="utf-8")

    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES

    def _render(error: str | None = None):
        runs = list(reversed(_load_runs()))
        return render_template_string(
            _INDEX_TEMPLATE, runs=runs, style=_PAGE_STYLE, script=_PAGE_SCRIPT, error=error
        )

    @app.route("/", methods=["GET"])
    def index():
        return _render()

    @app.errorhandler(413)
    def too_large(_exc):
        return _render("Upload too large — the dashboard's demo limit is 25 MB."), 413

    @app.route("/upload", methods=["POST"])
    def upload():
        file = request.files.get("project")
        if file is None or file.filename == "":
            return redirect(url_for("index"))

        run_id = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]
        run_dir = runs_root / run_id
        src_dir = run_dir / "src"
        out_dir = run_dir / "out"
        src_dir.mkdir(parents=True, exist_ok=True)

        filename = file.filename
        suffix = Path(filename).suffix.lower()

        try:
            if suffix == ".zip":
                tmp_zip = run_dir / "upload.zip"
                file.save(tmp_zip)
                with zipfile.ZipFile(tmp_zip) as zf:
                    _safe_extract_zip(zf, src_dir)
                tmp_zip.unlink(missing_ok=True)
                scan_root = _single_project_dir(src_dir)
            elif suffix in ALLOWED_SINGLE_FILE_EXT:
                file.save(src_dir / filename)
                scan_root = src_dir
            else:
                raise UploadError(
                    f"Unsupported file type '{suffix or filename}'. "
                    "Upload a .zip of your PHP project, or a single .php file."
                )

            doc_file = request.files.get("migration_notes")
            doc_path = None
            if doc_file is not None and doc_file.filename:
                doc_path = run_dir / doc_file.filename
                doc_file.save(doc_path)

            summary = run_pipeline(scan_root, out_dir, doc_path)
        except (UploadError, zipfile.BadZipFile) as exc:
            shutil.rmtree(run_dir, ignore_errors=True)
            return _render(str(exc)), 400
        except Exception:
            # Log the full traceback server-side only -- never show it to the
            # browser. (This is exactly the LL008 pattern this tool itself
            # flags in scanned code: don't leak stack traces to the client.)
            traceback.print_exc()
            shutil.rmtree(run_dir, ignore_errors=True)
            return _render(
                "Scan failed unexpectedly. Check the server logs for details."
            ), 500

        runs = _load_runs()
        runs.append({"id": run_id, "name": filename, "time": time.strftime("%Y-%m-%d %H:%M:%S"), **summary})
        _save_runs(runs)
        return redirect(url_for("report_file", run_id=run_id, filename="report.html"))

    @app.route("/runs/<run_id>/<path:filename>")
    def report_file(run_id: str, filename: str):
        out_dir = (runs_root / run_id / "out").resolve()
        if runs_root.resolve() not in out_dir.parents or not out_dir.exists():
            abort(404)
        return send_from_directory(str(out_dir), filename)

    return app


def main(host: str = "127.0.0.1", port: int = 8788, data_dir: str = "legacylift_dashboard_data") -> None:
    app = create_app(Path(data_dir))
    print(f"LegacyLift dashboard running at http://{host}:{port}  (data: {Path(data_dir).resolve()})")
    app.run(host=host, port=port)
