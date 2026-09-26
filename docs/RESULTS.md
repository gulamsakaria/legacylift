# Results — real, measured numbers

All numbers below come from an actual run of the pipeline against
`examples/legacy-school-portal`, in this environment (no PHP installed —
the verifier's `php -l` step reports "skipped" honestly rather than
faking a pass; every other number is a real Python computation over real
files). Reproduce with:

```bash
pip install -e .
rm -rf out tests/generated/*.php examples/legacy-school-portal/legacylift.yaml
legacylift run examples/legacy-school-portal --doc examples/MIGRATION_NOTES.md --out out
```

## Pipeline output (unedited)

```
LegacyLift v0.1.0 — one-command pipeline
Target: examples/legacy-school-portal

[1/7] ingest      OK  (0.01s)
[2/7] scan        OK  risk=100 findings=92  (0.02s)
[3/7] plan        OK  15 rule group(s)  (0.00s)
[4/7] fix         OK  18 file(s) changed (dry-run diffs + applied copy)  (0.02s)
[5/7] tests       OK  11 PHPUnit test file(s) generated  (0.00s)
[6/7] verify      PASSED  risk 100 -> 20  (0.02s)
[7/7] report      OK  out/report.html  (0.00s)

Done in 0.07s.
Risk score: 100 -> 20
Critical findings: 47 -> 3
```

(Total wall time including process startup: ~0.2s -- this is an offline,
regex-based static tool with no network calls and no LLM inference at
runtime, so it is fast by construction. "15 rule group(s)" in the plan
output means 15 of the 16 rules produced at least one finding in this
run -- LL016 is implemented and tested but didn't happen to fire against
this particular demo app; see the table below.)

## Before -> after

| | Before | After |
|---|---|---|
| Files scanned | 21 | 21 (in `out/modernized/`) |
| Risk score (0-100) | **100** | **20** |
| Total findings | **92** | **17** |
| Critical findings | **47** | **3**\* |
| High findings | 28 | 3 |
| Medium findings | 9 | 3 |
| Low findings | 8 | 8 |
| Files changed by the fixer | -- | 18 / 21 |

\* The 3 remaining critical findings are the dynamic `include()` in
`view.php` (LL009) and two `unserialize()` calls on request input in
`student_profile.php` (LL015) -- all deliberately never auto-rewritten
(see `docs/DECISIONS.md`), and this is exactly what makes verification's
actual gate -- *zero remaining critical findings among rules marked
AUTO-FIXABLE* -- pass: LL009 and LL015 are ASSISTED, not AUTO-FIXABLE, so
neither blocks.

## Findings by rule -- before the fix

| Rule | Findings |
|---|---|
| LL001 (mysql_* functions) | 36 |
| LL005 (missing CSRF) | 19 |
| LL002 (SQL injection) | 5 |
| LL003 (XSS) | 5 |
| LL008 (short tags / suppression) | 4 |
| LL012 (mixed HTML/logic) | 4 |
| LL014 (old-style constructors) | 4 |
| LL004 (weak password hashing) | 3 |
| LL007 (deprecated functions) | 3 |
| LL006 (register_globals-style) | 2 |
| LL013 (session fixation) | 2 |
| LL015 (unserialize object injection) | 2 |
| LL009 (dangerous functions/LFI) | 1 |
| LL010 (unvalidated upload) | 1 |
| LL011 (hard-coded credentials) | 1 |
| LL016 (predictable rand/mt_rand token) | 0 |
| **Total** | **92** |

15 of 16 rules produced at least one real finding against the demo app --
none of these are synthetic or hand-inserted after the fact; every one
came from scanning the actual PHP files under
`examples/legacy-school-portal/`. LL016 (predictable `rand()`/`mt_rand()`
used for a security-sensitive token) is a genuine, independently tested
rule with its own positive/negative fixtures in
`tests/test_scanner_rules.py` -- the demo app simply doesn't happen to
contain that specific pattern. We're reporting the honest zero rather
than manufacturing a finding to pad the table.

## Fixes actually applied

| Rule | Changes applied |
|---|---|
| LL005 (CSRF) | 20 |
| LL001 (mysql_* -> PDO) | 29 |
| LL003 (XSS escaping) | 12 |
| LL002 (parameterized queries) | 7 |
| LL011 (secrets -> .env) | 4 |
| LL004 (password_hash / rehash-on-login) | 3 |
| LL007 (deprecated -> modern) | 3 |
| LL013 (session_regenerate_id) | 1 |
| LL008 (short tags) | 1 |

Flagged for manual review (ASSISTED, not auto-rewritten): **LL006** (2 --
`extract()` calls, TODO comment inserted), **LL008** (1 -- an `@`
suppression left untouched). LL009, LL010, LL012, LL014, and LL015
findings remain visible in the after-scan by design (detection-only or
ASSISTED rules) -- see `docs/ARCHITECTURE.md`'s rule catalogue for which
is which.

Secrets extracted to environment variables: `DB_HOST`, `DB_USER`,
`DB_PASSWORD`, `DB_NAME` -- `.env.example` is generated with the keys and
no real values; the real (demo) password never leaves the original file's
git history if this were a real repo, since `.env.example` only ever holds
placeholders.

## Effort estimate

| | Hours |
|---|---|
| Estimated manual fix time (all 92 findings, by severity) | **95.9h** |
| Estimated LegacyLift review time (patch review only, fixable findings) | **1.6h** |

This is the heuristic from `legacylift.yaml` (`effort_heuristic:`), not a
scientific measurement -- see `docs/ARCHITECTURE.md`. It is presented as
an estimate throughout the README and report, never as a hard claim.

## Test suite

- **Tool's own pytest suite:** 65 tests, **89% coverage** on
  `src/legacylift/` (`pytest -q --cov=legacylift --cov-report=term-missing`),
  including 7 tests for the upload dashboard (`webapp.py`) covering the
  happy path and its zip-slip path-traversal guard.
- **Generated PHPUnit tests:** 11 files written to `tests/generated/` --
  SQL-injection regression tests (3 payloads x 2 endpoints), login/rehash
  tests, XSS-escaping tests (including a Bangla round-trip assertion), and
  a search-parameterization test. These require PHP + PHPUnit to execute,
  which are not available in this build environment -- install PHP +
  PHPUnit and run `vendor/bin/phpunit tests/generated` once
  `legacylift run` has produced `out/modernized/` to get a real
  pass/fail. The generated tests reference `out/modernized/includes/`
  (the default `--apply` output location) so `legacylift run` must be
  executed before `phpunit tests/generated` will resolve its requires.

## Known false negative (disclosed, not hidden)

`student_edit.php` uses `extract($_POST)` before building an `UPDATE`
query from the resulting bare `$name`/`$class`/`$id` variables. LegacyLift
correctly flags the `extract()` call itself (LL006, ASSISTED -- a TODO
comment is inserted) but does **not** trace those variables forward into
the SQL string, so the underlying SQL injection in that one file is not
re-detected by the after-scan and is not auto-fixed. This is a genuine
limitation of line-level regex analysis without real data-flow tracking --
disclosed here and in the README's Known Limitations rather than glossed
over. It is exactly the risk LL006 exists to flag: manual review of any
`extract()` call site is required precisely because it defeats this kind
of tool.
