"""Group scan findings into a prioritised migration plan.

Ordering: security-critical rules first, then compatibility (deprecated/
removed functions), then structural cleanup. Each item is classified as
AUTO-FIXABLE (the fixer has a safe automated rewrite), ASSISTED (LegacyLift
flags it with a TODO but a human must finish it), or MANUAL (detection only).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .scanner.engine import Finding, ScanResult
from .scanner.rules import RULES_BY_ID

_SECURITY_RULES = {"LL002", "LL003", "LL004", "LL005", "LL009", "LL011", "LL013", "LL015", "LL016"}
_COMPAT_RULES = {"LL001", "LL006", "LL007", "LL008"}
_STRUCTURE_RULES = {"LL010", "LL012", "LL014"}

_CATEGORY_ORDER = {"security": 0, "compatibility": 1, "structure": 2}


def _category(rule_id: str) -> str:
    if rule_id in _SECURITY_RULES:
        return "security"
    if rule_id in _COMPAT_RULES:
        return "compatibility"
    return "structure"


def _classification(rule_id: str, fixable: bool) -> str:
    if not fixable:
        # LL009 and LL010 are deliberately not silently auto-fixed (code
        # execution / upload paths are too risky to rewrite blind) but do
        # get concrete assisted guidance; LL012/LL014 are detection-only.
        if rule_id in {"LL006", "LL009", "LL010", "LL015"}:
            return "ASSISTED"
        return "MANUAL"
    return "AUTO-FIXABLE"


@dataclass
class PlanItem:
    rule_id: str
    title: str
    severity: str
    category: str
    classification: str
    finding_count: int
    files: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "title": self.title,
            "severity": self.severity,
            "category": self.category,
            "classification": self.classification,
            "finding_count": self.finding_count,
            "files": self.files,
        }


_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def build_plan(scan: ScanResult) -> list[PlanItem]:
    grouped: dict[str, list[Finding]] = {}
    for f in scan.findings:
        grouped.setdefault(f.rule_id, []).append(f)

    items: list[PlanItem] = []
    for rule_id, findings in grouped.items():
        rule = RULES_BY_ID[rule_id]
        files = sorted({f.file for f in findings})
        items.append(
            PlanItem(
                rule_id=rule_id,
                title=rule.title,
                severity=rule.severity,
                category=_category(rule_id),
                classification=_classification(rule_id, rule.fixable),
                finding_count=len(findings),
                files=files,
            )
        )

    items.sort(
        key=lambda it: (
            _CATEGORY_ORDER[it.category],
            _SEVERITY_ORDER.get(it.severity, 9),
            it.rule_id,
        )
    )
    return items


def write_plan(items: list[PlanItem], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "plan.json").write_text(
        json.dumps([it.to_dict() for it in items], indent=2), encoding="utf-8"
    )

    lines = ["# Migration Plan", "", "Ordered: security-critical → compatibility → structure.", ""]
    lines.append("| Order | Rule | Title | Severity | Category | Classification | Findings |")
    lines.append("|---|---|---|---|---|---|---|")
    for idx, it in enumerate(items, 1):
        lines.append(
            f"| {idx} | {it.rule_id} | {it.title} | {it.severity} | {it.category} "
            f"| {it.classification} | {it.finding_count} |"
        )
    lines.append("")
    for it in items:
        lines.append(f"## {it.rule_id} — {it.title} ({it.classification})")
        lines.append(f"- Severity: **{it.severity}**  ·  Category: {it.category}  ·  "
                      f"Findings: {it.finding_count}")
        lines.append("- Files:")
        for f in it.files:
            lines.append(f"  - `{f}`")
        lines.append("")

    (out_dir / "plan.md").write_text("\n".join(lines), encoding="utf-8")
