# scanner-agent

**Owns:** `src/legacylift/scanner/` — the detection engine and all LLxxx rules.

**Responsibilities**
- Implement and unit-test each rule (LL001–LL014): pattern, severity, message,
  fixable flag, file/line/snippet capture.
- Keep false positives low: skip matches inside comments/strings that only
  *mention* a dangerous function, skip code already wrapped in the project's
  own safe helpers (`htmlspecialchars`, prepared statements, `password_hash`).
- Compute per-file and per-project Risk Score using the formula in
  `legacylift.yaml` / `docs/ARCHITECTURE.md`.
- Hand off a stable, ordered `Finding` list (JSON-serialisable) to the
  planner, fixer, and report agents.

**Definition of done:** every rule has a positive and negative fixture test;
scanning the demo app yields ≥40 findings across all 14 rules with the
documented risk score.
