from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .rules import RULES, RULES_BY_ID

MAX_FILE_SIZE_DEFAULT_KB = 5000


@dataclass
class Finding:
    rule_id: str
    severity: str
    title: str
    fixable: bool
    file: str
    line: int
    snippet: str
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "title": self.title,
            "fixable": self.fixable,
            "file": self.file,
            "line": self.line,
            "snippet": self.snippet,
            "explanation": self.explanation,
        }


@dataclass
class FileResult:
    path: str
    findings: list[Finding] = field(default_factory=list)
    risk_score: float = 0.0


@dataclass
class ScanResult:
    root: str
    files_scanned: int
    files: list[FileResult]
    findings: list[Finding]
    project_risk_score: int
    findings_by_rule: dict[str, int]
    findings_by_severity: dict[str, int]
    estimated_manual_hours: float
    estimated_legacylift_hours: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "root": self.root,
            "files_scanned": self.files_scanned,
            "project_risk_score": self.project_risk_score,
            "findings_by_rule": self.findings_by_rule,
            "findings_by_severity": self.findings_by_severity,
            "estimated_manual_hours": round(self.estimated_manual_hours, 2),
            "estimated_legacylift_hours": round(self.estimated_legacylift_hours, 2),
            "findings": [f.to_dict() for f in self.findings],
            "files": [
                {"path": fr.path, "risk_score": fr.risk_score, "finding_count": len(fr.findings)}
                for fr in self.files
            ],
        }


def _is_template_file(path: Path) -> bool:
    return path.suffix.lower() == ".phtml"


def _iter_target_files(root: Path, cfg: dict):
    scan_cfg = cfg.get("scan", {})
    extensions = set(scan_cfg.get("extensions", [".php", ".inc", ".phtml"]))
    exclude_dirs = set(scan_cfg.get("exclude_dirs", []))
    follow_symlinks = scan_cfg.get("follow_symlinks", False)
    max_size_bytes = scan_cfg.get("max_file_size_kb", MAX_FILE_SIZE_DEFAULT_KB) * 1024

    for dirpath, dirnames, filenames in os.walk(root, followlinks=follow_symlinks):
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs and not d.startswith(".git")]
        for fname in filenames:
            fpath = Path(dirpath) / fname
            if fpath.suffix.lower() not in extensions:
                continue
            if not follow_symlinks and fpath.is_symlink():
                real = fpath.resolve()
                try:
                    real.relative_to(root.resolve())
                except ValueError:
                    continue  # refuse symlinks pointing outside the target tree
            try:
                if fpath.stat().st_size > max_size_bytes:
                    continue
            except OSError:
                continue
            yield fpath


def scan_file(fpath: Path, cfg: dict, only_rules: list[str] | None = None) -> FileResult:
    try:
        text = fpath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return FileResult(path=str(fpath))
    lines = text.splitlines()
    is_template = _is_template_file(fpath)

    weights = cfg.get("risk", {}).get(
        "severity_weight", {"critical": 40, "high": 20, "medium": 8, "low": 3}
    )

    findings: list[Finding] = []
    rules = [RULES_BY_ID[r] for r in only_rules] if only_rules else RULES
    for rule in rules:
        for line_no, snippet, explanation in rule.detect(lines, fpath, is_template):
            findings.append(
                Finding(
                    rule_id=rule.id,
                    severity=rule.severity,
                    title=rule.title,
                    fixable=rule.fixable,
                    file=str(fpath),
                    line=line_no,
                    snippet=snippet,
                    explanation=explanation,
                )
            )

    raw_score = sum(weights.get(f.severity, 5) for f in findings)
    file_risk = min(100.0, float(raw_score))
    return FileResult(path=str(fpath), findings=findings, risk_score=file_risk)


def scan_path(root: Path, cfg: dict, only_rules: list[str] | None = None) -> ScanResult:
    root = Path(root)
    file_results: list[FileResult] = []
    for fpath in sorted(_iter_target_files(root, cfg)):
        file_results.append(scan_file(fpath, cfg, only_rules))

    all_findings: list[Finding] = []
    for fr in file_results:
        all_findings.extend(fr.findings)

    files_scanned = len(file_results)
    risk_cfg = cfg.get("risk", {})
    scale_factor = risk_cfg.get("scale_factor", 3.2)
    if files_scanned:
        avg_file_risk = sum(fr.risk_score for fr in file_results) / files_scanned
        # Project risk = mean normalized file risk, pulled up by scale_factor so a
        # few critical files in an otherwise-clean tree still read as high risk.
        # See docs/ARCHITECTURE.md for the worked example.
        project_risk = min(100, round(avg_file_risk * (1 + (scale_factor - 1) * 0.6)))
    else:
        project_risk = 0

    findings_by_rule: dict[str, int] = {}
    findings_by_severity: dict[str, int] = {}
    for f in all_findings:
        findings_by_rule[f.rule_id] = findings_by_rule.get(f.rule_id, 0) + 1
        findings_by_severity[f.severity] = findings_by_severity.get(f.severity, 0) + 1

    effort_cfg = cfg.get("effort_heuristic", {})
    hours_per = effort_cfg.get(
        "hours_per_finding", {"critical": 1.5, "high": 0.75, "medium": 0.35, "low": 0.15}
    )
    ll_hours_per = effort_cfg.get("legacylift_hours_per_finding", 0.02)
    manual_hours = sum(hours_per.get(f.severity, 0.2) for f in all_findings)
    ll_hours = sum(ll_hours_per for f in all_findings if f.fixable)

    return ScanResult(
        root=str(root),
        files_scanned=files_scanned,
        files=file_results,
        findings=all_findings,
        project_risk_score=int(project_risk),
        findings_by_rule=findings_by_rule,
        findings_by_severity=findings_by_severity,
        estimated_manual_hours=manual_hours,
        estimated_legacylift_hours=ll_hours,
    )
