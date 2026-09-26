from __future__ import annotations

import difflib
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import fixes
from .templates import AUTH_PHP, CSRF_PHP, DB_PHP, ENV_PHP, ESCAPE_PHP

_HELPER_FILES = {
    "includes/db.php": DB_PHP,
    "includes/escape.php": ESCAPE_PHP,
    "includes/auth.php": AUTH_PHP,
    "includes/csrf.php": CSRF_PHP,
    "includes/env.php": ENV_PHP,
}


@dataclass
class FileFixOutcome:
    path: str
    changed: bool
    applied: list[str] = field(default_factory=list)
    assisted: list[str] = field(default_factory=list)
    diff: str = ""


@dataclass
class FixResult:
    mode: str
    files: list[FileFixOutcome]
    applied_by_rule: dict[str, int]
    assisted_by_rule: dict[str, int]
    env_keys: dict[str, str]
    modernized_root: Path | None
    patches_dir: Path

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "files_changed": sum(1 for f in self.files if f.changed),
            "applied_by_rule": self.applied_by_rule,
            "assisted_by_rule": self.assisted_by_rule,
            "env_keys": list(self.env_keys.keys()),
            "modernized_root": str(self.modernized_root) if self.modernized_root else None,
        }


def _is_do_not_touch(relpath: str, do_not_touch: list[str]) -> bool:
    return any(pattern.strip("/").rstrip("/") in relpath for pattern in do_not_touch if pattern.strip())


def _apply_fix_chain(text: str) -> tuple[str, dict[str, list[str]], dict[str, list[str]], dict[str, str]]:
    applied: dict[str, list[str]] = {}
    assisted: dict[str, list[str]] = {}
    env_keys: dict[str, str] = {}

    def record(rule_id, a, s):
        if a:
            applied.setdefault(rule_id, []).extend(a)
        if s:
            assisted.setdefault(rule_id, []).extend(s)

    text, a, s = fixes.fix_ll002_parameterize(text)
    record("LL002", a, s)
    text, a, s = fixes.fix_ll001_mysql_to_pdo(text)
    record("LL001", a, s)
    text, a, s = fixes.fix_ll003_escape_output(text)
    record("LL003", a, s)
    text, a, s = fixes.fix_ll004_password_hash(text)
    record("LL004", a, s)
    text, a, s = fixes.fix_ll005_csrf(text)
    record("LL005", a, s)
    text, a, s = fixes.fix_ll006_flag_extract(text)
    record("LL006", a, s)
    text, a, s = fixes.fix_ll007_deprecated(text)
    record("LL007", a, s)
    text, a, s = fixes.fix_ll008_short_tags(text)
    record("LL008", a, s)
    text, a, s, keys = fixes.fix_ll011_env_secrets(text)
    record("LL011", a, s)
    env_keys.update(keys)
    text, a, s = fixes.fix_ll013_session_regen(text)
    record("LL013", a, s)

    return text, applied, assisted, env_keys


def _unified_diff(relpath: str, before: str, after: str) -> str:
    before_lines = before.splitlines(keepends=True)
    after_lines = after.splitlines(keepends=True)
    diff = difflib.unified_diff(
        before_lines, after_lines, fromfile=f"a/{relpath}", tofile=f"b/{relpath}"
    )
    return "".join(diff)


def run_fixer(
    source_root: Path,
    cfg: dict,
    out_dir: Path,
    apply: bool = False,
    in_place: bool = False,
    only_rules: list[str] | None = None,
) -> FixResult:
    """Run the full fix chain over every scan-eligible file.

    Always writes unified diffs to ``out_dir/patches/``. If ``apply`` is
    True, also writes a fully modernized copy to ``out_dir/modernized/``.
    If ``in_place`` is True, writes fixed content directly back into
    ``source_root`` (caller is responsible for requiring an explicit
    confirmation flag before setting this).
    """
    from ..scanner.engine import _iter_target_files  # reuse the same file walk

    source_root = Path(source_root)
    patches_dir = out_dir / "patches"
    patches_dir.mkdir(parents=True, exist_ok=True)
    modernized_root = out_dir / "modernized" if apply else None

    if apply and modernized_root is not None:
        if modernized_root.exists():
            shutil.rmtree(modernized_root)
        ignore_names = [".git", "__pycache__", "*.pyc"]
        try:
            rel_out = out_dir.resolve().relative_to(source_root.resolve())
            if rel_out.parts:
                ignore_names.append(rel_out.parts[0])
        except ValueError:
            pass  # out_dir is not inside source_root — nothing extra to ignore
        shutil.copytree(
            source_root,
            modernized_root,
            ignore=shutil.ignore_patterns(*ignore_names),
        )

    do_not_touch = cfg.get("constraints", {}).get("do_not_touch_paths", []) or []

    outcomes: list[FileFixOutcome] = []
    total_applied: dict[str, int] = {}
    total_assisted: dict[str, int] = {}
    all_env_keys: dict[str, str] = {}
    any_fix_applied = False

    for fpath in sorted(_iter_target_files(source_root, cfg)):
        # Always forward-slash, even on Windows: this is used to build the
        # flattened patch filename below (relpath.replace("/", "__")) and to
        # match do-not-touch patterns, both of which assume "/" as written
        # in legacylift.yaml / migration-notes docs.
        relpath = fpath.relative_to(source_root).as_posix()
        if _is_do_not_touch(relpath, do_not_touch):
            continue

        original = fpath.read_text(encoding="utf-8", errors="replace")
        new_text, applied, assisted, env_keys = _apply_fix_chain(original)
        all_env_keys.update(env_keys)

        changed = new_text != original
        applied_flat = [f"[{rid}] {msg}" for rid, msgs in applied.items() for msg in msgs]
        assisted_flat = [f"[{rid}] {msg}" for rid, msgs in assisted.items() for msg in msgs]
        for rid, msgs in applied.items():
            total_applied[rid] = total_applied.get(rid, 0) + len(msgs)
        for rid, msgs in assisted.items():
            total_assisted[rid] = total_assisted.get(rid, 0) + len(msgs)

        diff_text = _unified_diff(relpath, original, new_text) if changed else ""
        outcomes.append(
            FileFixOutcome(path=relpath, changed=changed, applied=applied_flat,
                            assisted=assisted_flat, diff=diff_text)
        )

        if changed:
            any_fix_applied = True
            patch_path = patches_dir / (relpath.replace("/", "__") + ".diff")
            patch_path.write_text(diff_text, encoding="utf-8")

            if apply and modernized_root is not None:
                (modernized_root / relpath).write_text(new_text, encoding="utf-8")
            if in_place:
                fpath.write_text(new_text, encoding="utf-8")

    # Generate/refresh helper files wherever fixes were actually applied.
    if any_fix_applied:
        write_root = modernized_root if apply else (source_root if in_place else None)
        for rel, content in _HELPER_FILES.items():
            diff_text = _unified_diff(rel, "", content)
            (patches_dir / (rel.replace("/", "__") + ".diff")).write_text(diff_text, encoding="utf-8")
            if write_root is not None:
                target = write_root / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")

        if all_env_keys:
            env_example = "\n".join(f"{k}=" for k in sorted(all_env_keys)) + "\n"
            if "DB_HOST" not in all_env_keys:
                env_example = "DB_HOST=localhost\nDB_NAME=legacy_school_portal\n" + env_example
            if write_root is not None:
                (write_root / ".env.example").write_text(env_example, encoding="utf-8")
            diff_text = _unified_diff(".env.example", "", env_example)
            (patches_dir / ".env.example.diff").write_text(diff_text, encoding="utf-8")

    mode = "in-place" if in_place else ("apply" if apply else "dry-run")
    return FixResult(
        mode=mode,
        files=outcomes,
        applied_by_rule=total_applied,
        assisted_by_rule=total_assisted,
        env_keys=all_env_keys,
        modernized_root=modernized_root,
        patches_dir=patches_dir,
    )
