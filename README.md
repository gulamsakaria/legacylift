# LegacyLift — Legacy PHP Modernizer

![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Tests: 65 passing](https://img.shields.io/badge/tests-65%20passing-brightgreen)

Point it at an old PHP codebase. Get a risk report, safe automated fixes,
generated tests, and a before/after proof — in minutes instead of weeks.

Built for the **IBM Bob 2.0 Hackathon** (lablab.ai, 25–27 Sep 2026) —
challenge: improve application maintenance / legacy modernization using
Bob 2.0's Agent mode, parallel subagents, and document understanding. See
`docs/BOB_USAGE.md` and `docs/PROBLEM_AND_SOLUTION.md`.

### Contents
[The problem](#the-problem) ·
[The solution](#the-solution) ·
[Quickstart](#60-second-quickstart) ·
[Install](#install) ·
[Usage](#usage) ·
[Dashboard](#dashboard-upload-your-own-code) ·
[Results](#results-real-not-staged) ·
[Tech stack](#tech-stack) ·
[Known limitations](#known-limitations)

## The problem

Thousands of small businesses, schools and news sites in emerging markets
still run PHP 5.x-era code: `mysql_*` functions, string-concatenated SQL,
`register_globals`-style variables, MD5 passwords, no CSRF protection,
unescaped output, HTML mixed with logic. Modernizing this by hand takes
weeks, is risky, and is usually skipped — leaving real sites vulnerable.

## The solution

A pipeline of six deterministic stages — **scan → plan → fix → generate
tests → verify → report** — built around 16 detection rules for the most
common PHP 5→8 modernization hazards. Every fix produces a
human-reviewable diff before anything is written; nothing changes
silently. Run against the included demo app (a small school portal), it
found **92 real findings across all 16 rules**, safely fixed most of them
automatically, generated PHPUnit regression tests, and dropped the risk
score from **100/100 to 20/100** — see `docs/RESULTS.md` for the real,
unedited numbers.

## 60-second quickstart

```bash
pip install -e .
legacylift run examples/legacy-school-portal --doc examples/MIGRATION_NOTES.md
open out/report.html   # or: legacylift serve --report-dir out
```

That's the whole demo. `out/report.html` is a single self-contained file —
before/after risk score, filterable findings table, every diff, dark-mode
aware, no external requests.

## Install

```bash
pip install -e .           # core
pip install -e ".[dev]"    # + pytest, ruff, black
pip install -e ".[serve]"  # + Flask for `legacylift serve` (falls back to
                            #   Python's stdlib http.server without it)
```

Requires Python 3.11+. No PHP installation is required to scan or fix —
LegacyLift works on the source text directly and degrades gracefully
(clearly reporting what it skipped) wherever a PHP toolchain isn't
available, exactly as the spec requires.

## Project website

`website/` is a landing page (problem/solution, the six-stage pipeline,
the full rule catalogue, real before/after numbers, a live embedded
sample report) **with a real "scan your code" upload form** backed by a
Python serverless function (`website/api/scan.py`) that runs the actual
pipeline — deployable to Vercel as-is. See `website/README.md` for deploy
steps and the function's known limits (~4 MB upload, no run history,
single-request timeout — by design, not bugs).

## Usage

```bash
legacylift scan <path>                          # risk report only
legacylift plan <path>                           # prioritised migration plan
legacylift ingest <doc> <path>                   # parse migration notes into legacylift.yaml
legacylift fix <path> --apply                    # safe fixes -> out/modernized/ (default: dry-run diffs only)
legacylift fix <path> --in-place --i-have-a-backup   # rewrite the source tree itself
legacylift tests <path>                          # generate PHPUnit tests
legacylift verify <path> --modernized out/modernized
legacylift serve --report-dir out                # browse the report locally
legacylift run <path> --doc MIGRATION_NOTES.md   # the whole pipeline, one command
legacylift dashboard                             # web UI: upload your own PHP project (.zip) and scan it
```

## Dashboard (upload your own code)

`legacylift scan`/`run` only take a local path — LegacyLift analyzes source
text directly, so it can't fetch a live URL (a browser only ever sees
rendered HTML, never the server's PHP source). To point it at your own
code without using the CLI:

```bash
pip install -e ".[serve]"
legacylift dashboard                # http://127.0.0.1:8788
```

Open it, upload a `.zip` of your PHP project (or drop in a single `.php`
file), optionally attach a migration-notes doc, and it runs the exact same
scan -> plan -> fix -> tests -> verify -> report pipeline as `legacylift
run`, then shows you the generated report. Each upload gets its own run
directory under `--data-dir` (default `legacylift_dashboard_data/`), and
past runs are listed on the dashboard's home page. Nothing is uploaded
anywhere external — it's a local Flask server on your own machine.

**Deploying the dashboard publicly:** it's a stateful Flask app (it writes
each run's output to disk under `--data-dir`), so it needs a real Python
host with a persistent filesystem — e.g. Render, Railway, Fly.io, or a
small VPS. It will **not** run as-is on Vercel's static/serverless hosting
(no writable filesystem between requests). For a quick, zero-backend
"Application URL", host `docs/sample-report/report.html` (or a fresh
`out/report.html`) as a static site instead — that works on Vercel/GitHub
Pages with no changes.

## Screenshots

*(placeholders — add your own before submitting)*

- `docs/bob-session-notes/` — Bob task-session screenshots
- `docs/sample-report/report.html` — a real generated report, open it directly

## Results (real, not staged)

| | Before | After |
|---|---|---|
| Risk score (0–100) | **100** | **20** |
| Total findings | **92** | **17** |
| Critical findings | **47** | **3**\* |
| Est. manual fix time | **95.9h** | — |
| Est. LegacyLift review time | — | **1.6h** |

\* The 3 remaining critical findings are a dangerous dynamic `include()`
(LL009) and two `unserialize()` calls on request input (LL015) —
deliberately never auto-rewritten, since a wrong guess there is worse than
no fix. See `docs/RESULTS.md` for the full breakdown and exact commands.

## Tech stack

- **Core engine:** Python 3.11+, CLI (`legacylift`) via `pyproject.toml` / `pip install -e .`
- **PHP analysis:** dependency-free, line-oriented regex rules (no
  tree-sitter — works with zero PHP toolchain installed, degrades
  gracefully where one would help, e.g. `php -l`)
- **Report:** self-contained HTML (inline CSS/JS, no CDN, dark-mode aware) + JSON + Markdown
- **Optional local UI:** `legacylift serve` (Flask if installed, stdlib `http.server` fallback)
- **Generated tests:** PHPUnit-style for the modernized PHP, `pytest` for the tool itself
- **No paid APIs, no network calls at runtime** — Bob is the development partner; the shipped tool needs no API key

## Known limitations

- **Regex-based, not a full AST/data-flow analyzer.** Every rule is
  unit-tested with positive and negative fixtures to keep false positives
  low, but static analysis without real data-flow has real false
  negatives. Concretely: `student_edit.php` in the demo app uses
  `extract($_POST)` before building a SQL query from the resulting bare
  variables — LegacyLift correctly flags the `extract()` call itself
  (LL006) but does not trace those variables into the later SQL string,
  so that specific SQL injection is not re-detected after fixing. See
  `docs/RESULTS.md`'s "Known false negative" section for the full
  explanation — this is exactly why `extract()` is flagged as high
  severity in the first place.
- **Some rules are detection-only or ASSISTED by design**, not because
  they were skipped: `extract()` removal (LL006), dangerous
  `eval`/`exec`/dynamic-include calls (LL009), and file-upload validation
  rules (LL010) all require a human decision LegacyLift cannot safely
  automate. See `docs/ARCHITECTURE.md`'s rule catalogue.
- **`php -l` and PHPUnit execution both need PHP installed**, which
  wasn't available in the environment this was built in — the verifier
  reports this honestly ("skipped") rather than faking a pass, and still
  completes its re-scan-based before/after comparison. Install PHP +
  PHPUnit and re-run `legacylift run ...` followed by
  `vendor/bin/phpunit tests/generated` to get a real pass/fail there.
- **Effort estimates are heuristics**, not measurements — configurable in
  `legacylift.yaml`, always presented as an estimate.

## License

MIT — see `LICENSE`.
