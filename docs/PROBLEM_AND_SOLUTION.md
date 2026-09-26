# Problem & Solution

**Problem.** Thousands of small businesses, schools and news sites in
emerging markets still run PHP 5.x-era code: `mysql_*` functions,
string-concatenated SQL, register_globals-style `extract()` calls, MD5
passwords, no CSRF protection, unescaped output. Modernizing this by hand
takes weeks, is risky on a codebase nobody fully remembers, and is usually
skipped — leaving real institutions (schools, clinics, local news outlets)
running code with known, exploitable weaknesses. Our own demo target is
exactly this: a small school's student/news portal, built years ago,
still running the site that indexes its Bangla-language news and holds
guardian phone numbers for every enrolled student.

**Solution.** LegacyLift is a pipeline of six deterministic stages —
scan, plan, fix, generate tests, verify, report — built around 16
detection rules covering the most common PHP 5→8 modernization hazards
(SQL injection, XSS, weak hashing, CSRF, object injection, deprecated
functions, and more). Every fix is a human-reviewable unified diff before
anything is written; nothing is changed silently. Run against our demo
school portal, it found **92 real findings across all 16 rules** in
**21 files**, safely fixed **75 of them automatically** (mysql_* → PDO,
SQL → parameterized queries, XSS escaping, weak hashing →
`password_hash()` with a zero-downtime rehash-on-login path, CSRF tokens,
secrets → `.env`), generated PHPUnit regression tests proving the
SQL-injection payloads that worked against the legacy code no longer do,
and dropped the project's risk score from **100/100 to 20/100** — all in
under a second, entirely offline, with **zero network calls and no API
key required at runtime**.

**Why this matters for the judging criteria.**
- *Application of Technology:* Bob 2.0's Agent mode drove the full build
  loop end-to-end; parallel subagents (`.bob/agents/*.md`) split scanner,
  security, refactor, test, report and docs work along real ownership
  boundaries; document understanding turned a plain-English migration-notes
  file into machine-checked constraints (`do_not_touch /uploads`, target
  PHP 8.2, preserve Bangla/UTF-8) that the fixer actually obeys.
- *Business value:* the effort heuristic estimates **95.9 hours of manual
  fix time** replaced by **1.6 hours of patch review** on this one small
  site — and the same tool scales to every other PHP 5-era codebase a
  school, clinic or local newsroom is quietly still running.
- *Originality:* rather than a chatbot wrapper, LegacyLift is a
  deterministic, offline, dependency-light toolchain that treats an LLM
  agent (Bob) as the *builder*, not a *runtime dependency* — the shipped
  tool needs no API key and makes no network calls, which matters directly
  for the kind of organisation this is built for.
- *Presentation:* one command, `legacylift run <path> --doc
  MIGRATION_NOTES.md`, produces a single polished HTML report with
  before/after risk scores, filterable findings, and every diff — see
  `docs/sample-report/report.html` and `docs/RESULTS.md` for the real,
  unedited run.
