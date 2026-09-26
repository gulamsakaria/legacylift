from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .planner import _SECURITY_RULES  # noqa: F401  (kept for future use)
from .scanner.engine import ScanResult, scan_path
from .scanner.rules import RULES_BY_ID

_AUTO_FIXABLE_RULES = {rid for rid, r in RULES_BY_ID.items() if r.fixable}


@dataclass
class LintResult:
    available: bool
    checked: int = 0
    failed: list[str] = field(default_factory=list)
    skipped_reason: str = ""


@dataclass
class VerifyResult:
    before: ScanResult
    after: ScanResult
    lint: LintResult
    remaining_critical_auto_fixable: list[str]
    passed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "before_risk_score": self.before.project_risk_score,
            "after_risk_score": self.after.project_risk_score,
            "before_findings": len(self.before.findings),
            "after_findings": len(self.after.findings),
            "before_by_severity": self.before.findings_by_severity,
            "after_by_severity": self.after.findings_by_severity,
            "lint": {
                "available": self.lint.available,
                "checked": self.lint.checked,
                "failed": self.lint.failed,
                "skipped_reason": self.lint.skipped_reason,
            },
            "remaining_critical_auto_fixable": self.remaining_critical_auto_fixable,
            "passed": self.passed,
        }


def run_php_lint(modernized_root: Path, cfg: dict) -> LintResult:
    php = shutil.which("php")
    if not php:
        return LintResult(available=False, skipped_reason="PHP is not installed in this "
                           "environment — syntax check skipped, degrading gracefully as "
                           "required. Re-scan-based verification below still applies.")
    extensions = set(cfg.get("scan", {}).get("extensions", [".php", ".inc", ".phtml"]))
    failed = []
    checked = 0
    for fpath in sorted(modernized_root.rglob("*")):
        if fpath.is_file() and fpath.suffix.lower() in extensions:
            checked += 1
            proc = subprocess.run([php, "-l", str(fpath)], capture_output=True, text=True)
            if proc.returncode != 0:
                failed.append(f"{fpath}: {proc.stdout.strip() or proc.stderr.strip()}")
    return LintResult(available=True, checked=checked, failed=failed)


def verify(before: ScanResult, modernized_root: Path, cfg: dict) -> VerifyResult:
    after = scan_path(modernized_root, cfg)
    lint = run_php_lint(modernized_root, cfg)

    remaining_critical_auto_fixable = sorted(
        {
            f"{f.rule_id} in {f.file}:{f.line}"
            for f in after.findings
            if f.severity == "critical" and f.rule_id in _AUTO_FIXABLE_RULES
        }
    )
    passed = not remaining_critical_auto_fixable and not lint.failed

    return VerifyResult(
        before=before,
        after=after,
        lint=lint,
        remaining_critical_auto_fixable=remaining_critical_auto_fixable,
        passed=passed,
    )
