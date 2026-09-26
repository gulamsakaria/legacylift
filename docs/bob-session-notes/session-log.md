# Bob 2.0 Session Log

This file is meant to hold a factual, chronological record of what was
actually done in real IBM Bob 2.0 sessions against this repository — not
a narrative written after the fact.

**How to fill this in:** after each Bob session, add one entry below with:
- the prompt you gave Bob (verbatim or summarized),
- what Bob actually changed (file list — Bob's own "N files changed"
  summary is a good source),
- the outcome (tests passing, pipeline run result), and
- a link to that session's screenshot in this same folder (see
  `SCREENSHOTS_README.md`).

Only write down what a screenshot or diff can back up. If a session's
summary claims something the diff doesn't show, don't record the claim.

---

## Session entries

**01 — Initial codebase read-through**
`01-initial-codebase-overview.png`
Prompt: "I need some changes on my code. First read my code properly."
Bob listed the project files, explored 7 + 2 files, then produced a
project-structure table (`cli.py`, `webapp.py`, `scanner/rules.py`,
`scanner/engine.py`, ...) summarizing the 6-stage pipeline before making
any change — plan before action.

**02–04 — Adding rule LL015 (`unserialize()` on request input), parallel agents**
`02-parallel-agents-ll015-kickoff.png`,
`03-parallel-agents-ll015-results.png`,
`04-ll015-before-after-pipeline.png`
Bob read the agent definitions and existing tests, then ran 4 tasks in
parallel across agent boundaries: `scanner-agent` added the rule to
`scanner/rules.py`, `test-agent` added parametrized positive/negative
tests to `test_scanner_rules.py`, `refactor-agent` added a new vulnerable
fixture (`student_profile.php` with two `unserialize()` calls on
`$_GET`/`$_POST`), `docs-agent` updated `ARCHITECTURE.md`'s rule table.
Result shown: 47 tests passing (was 43), then a real pipeline re-run
comparing LL001–014 vs LL001–015: risk 100→100 (still capped), findings
87→92, critical 43→47, LL015 hits 0→2 found in the new fixture file at
the exact lines added — the rule fired on real code it hadn't seen
before, not just its own unit tests.

**05 — Migration-notes document understanding (`preserve_existing_logins`)**
`05-migration-notes-preserve-logins.png`
Bob read `ARCHITECTURE.md`'s "Document understanding" section and
`auth.php`'s template to confirm existing behavior, edited 3 files, then
ran the full suite: 49 passed. Added `_PRESERVE_LOGINS_RE` to
`ingest.py`, matching phrasings like "logins must keep working" / "no
forced (mass) password reset" / "keep existing logins working" — this is
the regex-based document-understanding step `docs/BOB_USAGE.md` claims,
shown actually being built and tested.

**06 — Adding rule LL016 (weak `rand()`/`mt_rand()` for security tokens)**
`06-ll016-weak-token-rule.png`
Edited 3 files, ran `pytest tests/ -v`: 50 passed, 0 failed. Added
`_WEAK_RAND_CALL`, `_TOKEN_VAR` (matches variable names containing
`token`/`csrf`/`nonce`/`secret`/`session_id`/`key`), and `_SESSION_WRITE`
regexes, combined in `detect_ll016()` — explained line by line, including
why it deliberately skips lines already using
`random_bytes`/`openssl_random_pseudo_bytes`.

**07–08 — SVG risk-score gauge in the HTML report**
`07-svg-risk-gauge-build.png`, `08-svg-risk-gauge-summary.png`
Planned a Jinja2 macro computing `stroke-dashoffset` from a risk score
(circumference ≈175.9 at r=28), a responsive 2-column `@media` rule, and
a test asserting the `<svg>` is present — then applied the diff, added
the test, ran the full suite (50 passed), and re-ran the real pipeline
(`legacylift run examples/legacy-school-portal --doc
examples/MIGRATION_NOTES.md --out out`) to regenerate `out/report.html`
with real numbers before opening it.

**09–12 — Pre-submission security/honesty audit**
`09-report-opened-security-audit-start.png`,
`10-presubmission-cleanup-steps.png`,
`11-cleanup-gitignore-verification.png`,
`12-final-security-honesty-audit.png`
After opening the generated report in the browser to confirm the gauge
rendered correctly, Bob was asked to clean up before submission. It read
every relevant file first, then: deleted 4 stale docs
(`DEMO_SCRIPT.md`, `SLIDES_OUTLINE.md`, `SUBMISSION_CHECKLIST.md`, the
old `bob-session-notes/session-log.md`), created `.gitignore`, reran
tests (50 passed) and the full pipeline (verify PASSED, risk 100→20),
and rewrote `session-log.md`. It then audited the repo for absolute
paths (`/home/`, `/Users/`, `C:\`) and real secrets — found none, except
the deliberate `LL011` test fixture in
`examples/legacy-school-portal/includes/config.php` (left as-is, since
that's a finding the scanner is supposed to catch) and a `hunter2` string
that's a `pytest.mark.parametrize` test fixture, not a real credential.
It also explicitly flagged, unprompted, that `README.md`'s headline
numbers (100→14, 87→15) no longer match a fresh run (now 100→20, 87→92)
because rules LL015/LL016 were added after those numbers were written —
and left updating them as a content decision for a human rather than
silently rewriting the claim. (Later corroborated independently:
`docs/RESULTS.md`'s frozen numbers were confirmed stale against a live
run for the same reason.)
