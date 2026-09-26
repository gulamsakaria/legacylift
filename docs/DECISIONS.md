# Decisions Log

Brief record of the calls made while building LegacyLift, and why.

## Build plan (initial)
1. Build the demo legacy app first (`examples/legacy-school-portal`) — it
   drives which detection rules matter and gives the fixer real code to
   target.
2. Scanner → planner → fixer → test generator → verifier → report →
   one-command pipeline (`legacylift run`), in that order, since each stage
   consumes the previous one's output.
3. Run the full pipeline on the demo app after each stage lands, fix
   failures immediately, log major steps in
   `docs/bob-session-notes/session-log.md`.
4. Record real, measured before/after numbers in `docs/RESULTS.md` — never
   fabricated.

## Key technical decisions

- **No tree-sitter.** The spec allows falling back to a tolerant
  tokenizer/regex approach if `tree-sitter-php` fails to install. Rather
  than add a compiled dependency that may not build in every judge's
  environment, LegacyLift goes straight to a careful, line-oriented
  regex engine. Every rule is independently unit-tested with positive and
  negative fixtures to keep false positives low despite not having a real
  AST.

- **Fixable vs. assisted is decided per rule, deliberately conservative.**
  LL001–LL005, LL007, LL008 (short tags only), LL011, LL013 have safe,
  mechanical automated fixes. LL006 (`extract()`), LL009 (eval/exec/LFI),
  and LL010 (unvalidated upload) are flagged (ASSISTED) rather than
  auto-rewritten, because a wrong automated rewrite there is worse than no
  rewrite — removing `extract()` safely requires knowing every variable
  name it produces downstream; disabling `eval()`/`exec()` call sites
  changes application behaviour outright; upload validation rules are a
  business decision (allowed extensions, size limits) the tool cannot
  invent safely. LL012 (mixed HTML/logic) and LL014 (old-style
  constructors) are detection-only — they are code-smell/refactor
  signals, not security bugs with a single safe rewrite.

- **LL004 fixer guards against corrupting SQL.** Early testing surfaced a
  real bug: rewriting `md5($_POST['password'])` to `password_hash(...)`
  unconditionally would silently break any query that still compared that
  hash inside SQL (`password_hash()` is salted/non-deterministic, so the
  bound value would never match a stored hash again). The fixer now
  detects SQL context and leaves those call sites ASSISTED instead of
  rewriting them — see `tests/test_fixer.py::test_fix_ll004_does_not_touch_md5_inside_sql_string`.

- **Rehash-on-login, not a forced reset.** `legacy_verify_password()`
  verifies against the existing md5 hash on a matching login and
  immediately re-hashes with `password_hash()`, persisting the upgrade.
  Existing users keep working through the migration with zero downtime —
  directly satisfies the "logins must keep working" constraint in
  `examples/MIGRATION_NOTES.md`.

- **SQL parameterization via a small expression parser, not string
  replacement.** `fixer/fixes.py::parameterize_query()` splits a PHP
  concatenation expression on top-level `.` (respecting quotes), turns
  every non-literal fragment into a bound parameter, and collapses a
  hand-quoted placeholder (`'` + value + `'`) down to a bare `?` — because
  legacy code almost always wraps the interpolated value in manual quotes,
  and a bound parameter must not be quoted.

- **Known, honest limitation: no cross-statement data-flow.** The fixer
  does not trace a value from `extract($_POST)` forward into a later SQL
  string built from the resulting bare variable — that specific case (see
  `student_edit.php`) is still SQL-injectable after modernization and is
  *not* re-flagged by the rescan, because tracking taint through
  `extract()` needs real data-flow analysis, not line-level regex. This is
  exactly why LL006 flags `extract()` itself as high-severity: the
  variable-name indirection it creates is dangerous precisely because it
  defeats this kind of tool. Documented in the README's Known Limitations.

- **Risk score formula.** `project_risk = mean(file_risk) scaled by
  (1 + (scale_factor - 1) * 0.6)`, where `file_risk` is the sum of each
  finding's severity weight, capped at 100 per file. The 0.6 pull-up
  factor means a handful of critical files in an otherwise-clean tree
  still reads as high risk in the headline number, rather than being
  diluted by dozens of clean files — see `docs/ARCHITECTURE.md` for the
  worked example against the demo app's real numbers.

- **CLI structure mirrors the pipeline stages exactly**
  (`ingest/scan/plan/fix/tests/verify/serve/run`) so each stage can be run,
  inspected, and re-run independently during development — which is how
  every bug in this log was actually found (by running one stage at a
  time against the demo app and a hand-written smoke-test file before
  wiring `run`).
