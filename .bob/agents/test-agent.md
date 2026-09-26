# test-agent

**Owns:** `src/legacylift/tests_gen.py`, `tests/generated/` (PHPUnit-style),
and the tool's own `tests/` pytest suite.

**Responsibilities**
- For each modernized helper/endpoint (login, search, insert, upload),
  generate a PHPUnit test class covering the happy path and the specific
  vulnerability class that used to exist there.
- Generate the SQL-injection regression tests handed off by security-agent
  in executable PHPUnit form.
- Write and maintain the pytest suite for LegacyLift itself (scanner rules,
  risk score math, fixer idempotency, report generation), targeting ≥80%
  coverage on `src/legacylift/`.
- Wire `docker-compose.yml` + `Makefile:demo-verify` to run legacy vs.
  modernized against a seeded DB, and design the graceful-degradation path
  (skip with a clear reason) when PHP/Docker is unavailable.

**Definition of done:** `pytest` green with coverage report; generated
PHPUnit SQLi tests demonstrably fail on legacy code, pass on modernized code.
