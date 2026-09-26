from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..fixer.engine import FixResult
from ..planner import PlanItem
from ..scanner.engine import ScanResult
from ..verifier import VerifyResult
from .html_report import render_html_report

_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _findings_table_md(scan: ScanResult, limit: int = 60) -> str:
    lines = ["| Severity | Rule | File | Line | Explanation |", "|---|---|---|---|---|"]
    findings = sorted(scan.findings, key=lambda f: (_SEVERITY_ORDER.get(f.severity, 9), f.rule_id))
    for f in findings[:limit]:
        lines.append(f"| {f.severity} | {f.rule_id} | `{f.file}` | {f.line} | {f.explanation} |")
    if len(findings) > limit:
        lines.append(f"| … | … | … | … | *{len(findings) - limit} more — see report.json* |")
    return "\n".join(lines)


def write_json_report(
    scan: ScanResult,
    plan: list[PlanItem],
    fix_result: FixResult | None,
    verify_result: VerifyResult | None,
    out_path: Path,
) -> None:
    data: dict[str, Any] = {
        "scan": scan.to_dict(),
        "plan": [p.to_dict() for p in plan],
    }
    if fix_result is not None:
        data["fix"] = fix_result.to_dict()
    if verify_result is not None:
        data["verify"] = verify_result.to_dict()
    out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def write_md_report(
    scan: ScanResult,
    plan: list[PlanItem],
    fix_result: FixResult | None,
    verify_result: VerifyResult | None,
    out_path: Path,
) -> None:
    lines = ["# LegacyLift Report", ""]
    lines.append(f"**Project:** `{scan.root}`  ·  **Files scanned:** {scan.files_scanned}  ·  "
                 f"**Risk score:** {scan.project_risk_score}/100")
    lines.append("")
    lines.append("## Findings by severity")
    for sev in ("critical", "high", "medium", "low"):
        lines.append(f"- **{sev}**: {scan.findings_by_severity.get(sev, 0)}")
    lines.append("")
    lines.append(f"**Estimated manual effort:** {scan.estimated_manual_hours:.1f}h  ·  "
                 f"**Estimated LegacyLift review effort:** {scan.estimated_legacylift_hours:.1f}h")
    lines.append("")

    if verify_result is not None:
        lines.append("## Before / after")
        lines.append(f"- Risk score: **{verify_result.before.project_risk_score}** → "
                     f"**{verify_result.after.project_risk_score}**")
        lines.append(f"- Findings: **{len(verify_result.before.findings)}** → "
                     f"**{len(verify_result.after.findings)}**")
        lines.append(f"- Critical findings: "
                     f"**{verify_result.before.findings_by_severity.get('critical', 0)}** → "
                     f"**{verify_result.after.findings_by_severity.get('critical', 0)}**")
        lines.append(f"- Verification: **{'PASSED' if verify_result.passed else 'FAILED'}**")
        lines.append("")

    if fix_result is not None:
        lines.append("## Fixes applied")
        for rid, count in sorted(fix_result.applied_by_rule.items()):
            lines.append(f"- `{rid}`: {count} change(s) applied")
        if fix_result.assisted_by_rule:
            lines.append("")
            lines.append("## Flagged for manual review (ASSISTED)")
            for rid, count in sorted(fix_result.assisted_by_rule.items()):
                lines.append(f"- `{rid}`: {count} item(s)")
        lines.append("")

    lines.append("## Migration plan")
    lines.append("| Order | Rule | Title | Severity | Classification | Findings |")
    lines.append("|---|---|---|---|---|---|")
    for idx, p in enumerate(plan, 1):
        lines.append(f"| {idx} | {p.rule_id} | {p.title} | {p.severity} | {p.classification} "
                     f"| {p.finding_count} |")
    lines.append("")

    lines.append("## Findings (top 60 by severity)")
    lines.append(_findings_table_md(scan))
    lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


def write_html_report(
    scan: ScanResult,
    plan: list[PlanItem],
    fix_result: FixResult | None,
    verify_result: VerifyResult | None,
    out_path: Path,
) -> None:
    html = render_html_report(scan, plan, fix_result, verify_result)
    out_path.write_text(html, encoding="utf-8")


def write_all_reports(
    scan: ScanResult,
    plan: list[PlanItem],
    fix_result: FixResult | None,
    verify_result: VerifyResult | None,
    out_dir: Path,
) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "json": out_dir / "report.json",
        "md": out_dir / "report.md",
        "html": out_dir / "report.html",
    }
    write_json_report(scan, plan, fix_result, verify_result, paths["json"])
    write_md_report(scan, plan, fix_result, verify_result, paths["md"])
    write_html_report(scan, plan, fix_result, verify_result, paths["html"])
    return paths
