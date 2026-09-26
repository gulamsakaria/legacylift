# Bob Usage

**Agent mode drove the whole build loop.** Working from the master prompt
in `legacylift_bob_master_prompt.md`, Bob planned briefly into this file's
sibling `DECISIONS.md`, then built in dependency order: demo app first
(it drives which rules matter) → scanner → planner → fixer → test
generator → verifier → report → the one-command pipeline. After every
stage, Bob ran the tool against both a small hand-written smoke-test file
and the real demo app, read the actual output, and fixed what was wrong
before moving on — this is where every bug below was actually caught, not
from reading the code by eye.

**Parallel subagents, real ownership boundaries.** Six roles are defined
in `.bob/agents/*.md` and map directly to the module layout:
`scanner-agent` owns the 16 detection rules and the risk-score math;
`security-agent` owns the security-critical rules (SQLi, XSS, weak
hashing, CSRF, LFI, hard-coded secrets, session fixation) and their
fixes; `refactor-agent` owns the non-security modernization (`mysql_*` →
PDO, deprecated functions, short tags); `test-agent` owns PHPUnit
generation and the tool's own pytest suite; `report-agent` owns the
HTML/JSON/Markdown output; `docs-agent` owns everything under `docs/`.
Scanner, fixer and report work ran as parallel tasks against independent
files before integrating in the CLI layer.

**Document understanding, checked not assumed.** `legacylift ingest`
parses `examples/MIGRATION_NOTES.md`'s plain English into structured
constraints (`target_php_version: "8.2"`, `keep_urls_unchanged: true`,
`do_not_touch_paths: [/uploads]`, `preserve_encoding: UTF-8`) merged into
`legacylift.yaml`, and the fixer actually reads `do_not_touch_paths`
before rewriting any file — this was verified by inspecting the generated
`legacylift.yaml` against the source document, not assumed to work.

**What Bob did faster than a human would.** Three real bugs were caught
by *running* the tool rather than reading it: (1) `mysql_query()` calls
with a literal string argument weren't being converted to PDO — verify
failed with 4 remaining critical findings until fixed; (2) the CSRF
handler-injection regex was too strict for an `if` condition with extra
`&&` clauses, silently skipping `manage_news.php`; (3) `LL004`'s
password-hash rewrite would have corrupted a SQL query if applied to an
`md5()` call still sitting inside SQL string concatenation — caught by a
dedicated regression test before it ever touched the demo app. Each fix
came from a run-observe-fix cycle in minutes, not a design review.

**Honest limit disclosed, not hidden.** The pipeline does not trace a
variable produced by `extract($_POST)` forward into a later SQL string —
see `docs/RESULTS.md`'s "Known false negative" section. Bob chose to
document this rather than claim data-flow analysis the regex engine
doesn't actually have.
