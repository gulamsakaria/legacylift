from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from colorama import Fore, Style, init as colorama_init

from . import __version__
from .config import load_config
from .fixer.engine import run_fixer
from .ingest import ingest as ingest_doc
from .planner import build_plan, write_plan
from .report import write_all_reports
from .scanner.engine import scan_path
from .tests_gen import generate_tests
from .verifier import verify as run_verify

colorama_init(autoreset=True)


def _c(text: str, color: str) -> str:
    return f"{color}{text}{Style.RESET_ALL}"


def _print_scan_summary(scan) -> None:
    sev_color = {
        "critical": Fore.RED, "high": Fore.YELLOW, "medium": Fore.CYAN, "low": Fore.BLUE
    }
    print(_c(f"\nRisk score: {scan.project_risk_score}/100", Fore.MAGENTA + Style.BRIGHT))
    print(f"Files scanned: {scan.files_scanned}  ·  Findings: {len(scan.findings)}")
    for sev in ("critical", "high", "medium", "low"):
        n = scan.findings_by_severity.get(sev, 0)
        print(f"  {_c(sev.ljust(9), sev_color.get(sev, ''))} {n}")
    print(f"Estimated manual effort: {scan.estimated_manual_hours:.1f}h  ·  "
          f"LegacyLift review effort: {scan.estimated_legacylift_hours:.1f}h")


def cmd_ingest(args) -> int:
    doc_path = Path(args.doc)
    project_path = Path(args.path)
    if not doc_path.exists():
        print(_c(f"Document not found: {doc_path}", Fore.RED))
        return 1
    constraints = ingest_doc(doc_path, project_path)
    print(_c(f"Ingested {doc_path} -> {project_path / 'legacylift.yaml'}", Fore.GREEN))
    print(json.dumps(constraints, indent=2, ensure_ascii=False))
    return 0


def cmd_scan(args) -> int:
    project_path = Path(args.path)
    cfg = load_config(project_path, Path(args.config) if args.config else None)
    scan = scan_path(project_path, cfg)
    if args.json:
        print(json.dumps(scan.to_dict(), indent=2))
    else:
        _print_scan_summary(scan)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "scan.json").write_text(json.dumps(scan.to_dict(), indent=2), encoding="utf-8")
    return 0


def cmd_plan(args) -> int:
    project_path = Path(args.path)
    cfg = load_config(project_path, Path(args.config) if args.config else None)
    scan = scan_path(project_path, cfg)
    plan = build_plan(scan)
    out_dir = Path(args.out)
    write_plan(plan, out_dir)
    print(_c(f"Plan written: {out_dir/'plan.md'}, {out_dir/'plan.json'}", Fore.GREEN))
    for idx, p in enumerate(plan, 1):
        print(f"  {idx:2d}. [{p.classification:13s}] {p.rule_id} — {p.title} ({p.finding_count})")
    return 0


def cmd_fix(args) -> int:
    project_path = Path(args.path)
    cfg = load_config(project_path, Path(args.config) if args.config else None)
    out_dir = Path(args.out)
    if args.in_place and not args.i_have_a_backup:
        print(_c("--in-place requires --i-have-a-backup to confirm you understand this "
                 "overwrites your source tree.", Fore.RED))
        return 1
    result = run_fixer(project_path, cfg, out_dir, apply=args.apply, in_place=args.in_place)
    changed = sum(1 for f in result.files if f.changed)
    print(_c(f"Fixer ({result.mode}): {changed} file(s) changed.", Fore.GREEN))
    for rid, count in sorted(result.applied_by_rule.items()):
        print(f"  applied  {rid}: {count}")
    for rid, count in sorted(result.assisted_by_rule.items()):
        print(f"  assisted {rid}: {count}")
    print(f"Patches: {result.patches_dir}")
    if result.modernized_root:
        print(f"Modernized copy: {result.modernized_root}")
    return 0


def cmd_tests(args) -> int:
    project_path = Path(args.path)
    cfg = load_config(project_path, Path(args.config) if args.config else None)
    scan = scan_path(project_path, cfg)
    out_dir = Path(args.out)
    written = generate_tests(scan, project_path, out_dir)
    print(_c(f"Generated {len(written)} PHPUnit test file(s) in {out_dir}", Fore.GREEN))
    for w in written:
        print(f"  {w}")
    return 0


def cmd_verify(args) -> int:
    project_path = Path(args.path)
    modernized = Path(args.modernized)
    cfg = load_config(project_path, Path(args.config) if args.config else None)
    before = scan_path(project_path, cfg)
    result = run_verify(before, modernized, cfg)
    status = _c("PASSED", Fore.GREEN + Style.BRIGHT) if result.passed else _c("FAILED", Fore.RED + Style.BRIGHT)
    print(f"\nVerification: {status}")
    print(f"Risk score: {result.before.project_risk_score} -> {result.after.project_risk_score}")
    print(f"Findings:   {len(result.before.findings)} -> {len(result.after.findings)}")
    if not result.lint.available:
        print(_c(f"php -l skipped: {result.lint.skipped_reason}", Fore.YELLOW))
    else:
        print(f"php -l: {result.lint.checked} checked, {len(result.lint.failed)} failed")
    if result.remaining_critical_auto_fixable:
        print(_c("Remaining critical AUTO-FIXABLE findings:", Fore.RED))
        for item in result.remaining_critical_auto_fixable:
            print(f"  - {item}")
    return 0 if result.passed else 2


def cmd_serve(args) -> int:
    try:
        from flask import Flask, send_from_directory
    except ImportError:
        print(_c("Flask not installed — install the 'serve' extra: "
                 "pip install -e '.[serve]'. Falling back to Python's stdlib http.server "
                 "on the report directory instead.", Fore.YELLOW))
        import http.server
        import socketserver

        report_dir = Path(args.report_dir)
        handler = lambda *a, **kw: http.server.SimpleHTTPRequestHandler(  # noqa: E731
            *a, directory=str(report_dir), **kw
        )
        with socketserver.TCPServer(("", args.port), handler) as httpd:
            print(_c(f"Serving {report_dir} at http://localhost:{args.port}", Fore.GREEN))
            httpd.serve_forever()
        return 0

    app = Flask(__name__)
    report_dir = Path(args.report_dir).resolve()

    @app.route("/")
    def index():
        return send_from_directory(str(report_dir), "report.html")

    @app.route("/<path:filename>")
    def files(filename):
        return send_from_directory(str(report_dir), filename)

    print(_c(f"Serving {report_dir} at http://localhost:{args.port}", Fore.GREEN))
    app.run(port=args.port)
    return 0


def cmd_dashboard(args) -> int:
    try:
        from .webapp import main as run_dashboard
    except ImportError as exc:
        print(_c(f"Dashboard requires Flask: pip install -e '.[serve]' ({exc})", Fore.RED))
        return 1
    run_dashboard(host=args.host, port=args.port, data_dir=args.data_dir)
    return 0


def cmd_run(args) -> int:
    project_path = Path(args.path)
    out_dir = Path(args.out)
    timings = {}
    t_all = time.time()

    def stage(name):
        return _StageTimer(name, timings)

    print(_c(f"LegacyLift v{__version__} — one-command pipeline", Fore.MAGENTA + Style.BRIGHT))
    print(f"Target: {project_path}\n")

    if args.doc:
        with stage("ingest"):
            ingest_doc(Path(args.doc), project_path)
        print(_c(f"[1/7] ingest      OK  ({timings['ingest']:.2f}s)", Fore.GREEN))
    else:
        print(_c("[1/7] ingest      skipped (no --doc given)", Fore.YELLOW))

    cfg = load_config(project_path)

    with stage("scan"):
        before_scan = scan_path(project_path, cfg)
    print(_c(f"[2/7] scan        OK  risk={before_scan.project_risk_score} "
             f"findings={len(before_scan.findings)}  ({timings['scan']:.2f}s)", Fore.GREEN))

    with stage("plan"):
        plan = build_plan(before_scan)
        write_plan(plan, out_dir)
    print(_c(f"[3/7] plan        OK  {len(plan)} rule group(s)  ({timings['plan']:.2f}s)", Fore.GREEN))

    with stage("fix"):
        fix_result = run_fixer(project_path, cfg, out_dir, apply=True)
    changed = sum(1 for f in fix_result.files if f.changed)
    print(_c(f"[4/7] fix         OK  {changed} file(s) changed (dry-run diffs + applied copy)  "
             f"({timings['fix']:.2f}s)", Fore.GREEN))

    with stage("tests"):
        written = generate_tests(before_scan, project_path, Path("tests/generated"))
    print(_c(f"[5/7] tests       OK  {len(written)} PHPUnit test file(s) generated  "
             f"({timings['tests']:.2f}s)", Fore.GREEN))

    with stage("verify"):
        verify_result = run_verify(before_scan, fix_result.modernized_root, cfg)
    status = "PASSED" if verify_result.passed else "FAILED"
    color = Fore.GREEN if verify_result.passed else Fore.RED
    print(_c(f"[6/7] verify      {status}  risk {verify_result.before.project_risk_score} -> "
             f"{verify_result.after.project_risk_score}  ({timings['verify']:.2f}s)", color))

    with stage("report"):
        paths = write_all_reports(before_scan, plan, fix_result, verify_result, out_dir)
    print(_c(f"[7/7] report      OK  {paths['html']}  ({timings['report']:.2f}s)", Fore.GREEN))

    total = time.time() - t_all
    print(_c(f"\nDone in {total:.2f}s.", Style.BRIGHT))
    print(f"Risk score: {verify_result.before.project_risk_score} -> "
          f"{verify_result.after.project_risk_score}")
    print(f"Critical findings: "
          f"{verify_result.before.findings_by_severity.get('critical', 0)} -> "
          f"{verify_result.after.findings_by_severity.get('critical', 0)}")
    return 0 if verify_result.passed else 2


class _StageTimer:
    def __init__(self, name, store):
        self.name = name
        self.store = store

    def __enter__(self):
        self.t0 = time.time()
        return self

    def __exit__(self, *exc):
        self.store[self.name] = time.time() - self.t0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="legacylift", description="Legacy PHP Modernizer")
    p.add_argument("--version", action="version", version=f"legacylift {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest", help="Parse a migration-notes doc into legacylift.yaml constraints")
    p_ingest.add_argument("doc")
    p_ingest.add_argument("path", nargs="?", default=".")
    p_ingest.set_defaults(func=cmd_ingest)

    p_scan = sub.add_parser("scan", help="Scan a PHP codebase for risk findings")
    p_scan.add_argument("path")
    p_scan.add_argument("--config")
    p_scan.add_argument("--out", default="out")
    p_scan.add_argument("--json", action="store_true")
    p_scan.set_defaults(func=cmd_scan)

    p_plan = sub.add_parser("plan", help="Build a prioritised migration plan")
    p_plan.add_argument("path")
    p_plan.add_argument("--config")
    p_plan.add_argument("--out", default="out")
    p_plan.set_defaults(func=cmd_plan)

    p_fix = sub.add_parser("fix", help="Apply safe automated fixes")
    p_fix.add_argument("path")
    p_fix.add_argument("--config")
    p_fix.add_argument("--out", default="out")
    p_fix.add_argument("--dry-run", action="store_true", default=True)
    p_fix.add_argument("--apply", action="store_true")
    p_fix.add_argument("--in-place", action="store_true")
    p_fix.add_argument("--i-have-a-backup", action="store_true")
    p_fix.set_defaults(func=cmd_fix)

    p_tests = sub.add_parser("tests", help="Generate PHPUnit tests")
    p_tests.add_argument("path")
    p_tests.add_argument("--config")
    p_tests.add_argument("--out", default="tests/generated")
    p_tests.set_defaults(func=cmd_tests)

    p_verify = sub.add_parser("verify", help="Verify a modernized copy against the original")
    p_verify.add_argument("path")
    p_verify.add_argument("--modernized", default="out/modernized")
    p_verify.add_argument("--config")
    p_verify.set_defaults(func=cmd_verify)

    p_serve = sub.add_parser("serve", help="Serve the HTML report locally")
    p_serve.add_argument("--report-dir", default="out")
    p_serve.add_argument("--port", type=int, default=8787)
    p_serve.set_defaults(func=cmd_serve)

    p_run = sub.add_parser("run", help="Run the full pipeline: ingest -> scan -> plan -> fix -> tests -> verify -> report")
    p_run.add_argument("path")
    p_run.add_argument("--doc")
    p_run.add_argument("--out", default="out")
    p_run.set_defaults(func=cmd_run)

    p_dashboard = sub.add_parser(
        "dashboard", help="Run a local web dashboard to upload PHP code and scan it (requires the 'serve' extra)"
    )
    p_dashboard.add_argument("--host", default="127.0.0.1")
    p_dashboard.add_argument("--port", type=int, default=8788)
    p_dashboard.add_argument("--data-dir", default="legacylift_dashboard_data")
    p_dashboard.set_defaults(func=cmd_dashboard)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
