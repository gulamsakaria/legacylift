# refactor-agent

**Owns:** non-security modernization: `mysql_*` → PDO (LL001), deprecated
functions (LL007), short tags / error-suppression abuse (LL008),
register_globals-style patterns (LL006), old-style constructors and missing
visibility (LL014), logic/template separation metric (LL012).

**Responsibilities**
- Generate `includes/db.php`, a single PDO connection helper
  (utf8mb4, `ERRMODE_EXCEPTION`), and rewrite every `mysql_*` call site to use
  it with bound parameters.
- Replace deprecated functions with modern equivalents
  (`ereg`→`preg_match`, `split`→`explode`/`preg_split`, remove
  `create_function`/`magic_quotes` checks).
- Convert short tags to full `<?php` tags; add `declare(strict_types=1)` only
  where a file's behaviour is provably unaffected.
- Flag (not auto-fix) heavy HTML/logic mixing as ASSISTED with a TODO
  explaining the suggested split.

**Definition of done:** modernized output passes `php -l` (when PHP is
available) and re-scans clean for every rule in its ownership.
