# Contributing to LegacyLift

Thanks for considering a contribution.

## Dev setup
```bash
pip install -e ".[dev]"
pytest -q
ruff check src tests
black src tests
```

## Adding a new detection rule
1. Add the rule definition to `src/legacylift/scanner/rules.py` (ID, severity,
   pattern, message, fixable flag). Follow the existing `LLxxx` numbering.
2. Add a positive and a negative case to the `test_rule_positive_and_negative`
   table in `tests/test_scanner_rules.py` (or a dedicated test function
   alongside it for anything that needs more than one line of code).
3. If the rule is auto-fixable, add the corresponding function in
   `src/legacylift/fixer/fixes.py` and register it.
4. Update `docs/ARCHITECTURE.md`'s rule catalogue table.
5. Run `pytest -q` — every rule needs both a positive and a negative test to
   guard against false positives.

## Code style
Ruff + Black, 100-column lines, type hints on public functions, small
functions over clever one-liners.
