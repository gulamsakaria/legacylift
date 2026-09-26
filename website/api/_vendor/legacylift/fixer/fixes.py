"""Atomic fix functions.

Each ``fix_llXXX`` function takes a file's full text and returns
``(new_text, applied: list[str], assisted: list[str])`` — a change log used
by the report and by ``docs/RESULTS.md``. Fixes are conservative: anything
that cannot be rewritten with confidence is left in place with a `// TODO
LegacyLift:` comment (ASSISTED) rather than guessed at.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Small PHP-expression helpers
# ---------------------------------------------------------------------------


def split_top_level_concat(expr: str) -> list[str]:
    """Split a PHP expression on top-level `.` (concatenation), respecting
    quoted strings so a `.` inside a string literal is not treated as an
    operator."""
    parts: list[str] = []
    buf = ""
    quote: str | None = None
    i = 0
    while i < len(expr):
        c = expr[i]
        if quote:
            buf += c
            if c == "\\" and i + 1 < len(expr):
                buf += expr[i + 1]
                i += 2
                continue
            if c == quote:
                quote = None
            i += 1
            continue
        if c in ("'", '"'):
            quote = c
            buf += c
            i += 1
            continue
        if c == ".":
            parts.append(buf)
            buf = ""
            i += 1
            continue
        buf += c
        i += 1
    if buf.strip():
        parts.append(buf)
    return [p for p in parts if p.strip()]


_INTERP_VAR = re.compile(r"\$\w+(\[[^\]]+\])?")


def parameterize_query(expr: str) -> tuple[str, list[str]]:
    """Turn a PHP expression that builds a SQL string (via concatenation
    and/or double-quote interpolation) into (query_with_placeholders,
    [param_expressions]). Placeholders are positional `?`."""
    parts = split_top_level_concat(expr)
    out: list[str] = []
    params: list[str] = []
    for part in parts:
        part = part.strip()
        if part[:1] in ("'", '"'):
            quote = part[0]
            inner = part[1:-1] if part.endswith(quote) else part[1:]
            if quote == '"':
                def repl(m):
                    params.append(m.group(0))
                    return "?"
                inner = _INTERP_VAR.sub(repl, inner)
            out.append(inner)
        else:
            params.append(part)
            out.append("?")
    query = "".join(out)
    # Legacy code commonly hand-quotes the interpolated value, e.g.
    # "... = '" . $val . "'" -> "... = '?'". A bound parameter must not be
    # quoted (PDO handles that), so collapse a quote pair immediately
    # around a placeholder.
    query = re.sub(r"'\?'", "?", query)
    query = re.sub(r'"\?"', "?", query)
    return query, params


def _php_string_literal(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


# ---------------------------------------------------------------------------
# LL002 + the mysql_query() call it feeds — parameterized query rewrite
# ---------------------------------------------------------------------------
_SQL_ASSIGN = re.compile(
    r"(?P<indent>[ \t]*)\$(?P<var>\w*sql\w*)\s*=\s*(?P<expr>.+?);", re.IGNORECASE
)
_MYSQL_QUERY_CALL = re.compile(
    r"(?P<indent>[ \t]*)\$(?P<result>\w+)\s*=\s*mysql_query\s*\(\s*\$(?P<var>\w+)\s*\)\s*;"
)
_SQL_KEYWORD = re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE)\b", re.IGNORECASE)
_REQUEST_INPUT = re.compile(r"\$_(GET|POST|REQUEST|COOKIE)\s*\[")


def fix_ll002_parameterize(text: str) -> tuple[str, list[str], list[str]]:
    applied: list[str] = []
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        m = _SQL_ASSIGN.search(line)
        if m and _SQL_KEYWORD.search(m.group("expr")) and _REQUEST_INPUT.search(m.group("expr")):
            var = m.group("var")
            new_query, params = parameterize_query(m.group("expr"))
            lines[i] = f'{m.group("indent")}${var} = {_php_string_literal(new_query)};'
            applied.append(
                f"Parameterized `${var}` query (line {i + 1}) — "
                f"{len(params)} value(s) bound instead of concatenated."
            )
            # Look ahead a few lines for the mysql_query($var) call site.
            for j in range(i + 1, min(i + 6, len(lines))):
                qm = _MYSQL_QUERY_CALL.search(lines[j])
                if qm and qm.group("var") == var:
                    indent = qm.group("indent")
                    result = qm.group("result")
                    params_php = ", ".join(params) if params else ""
                    lines[j] = (
                        f"{indent}$__stmt = $pdo->prepare(${var});\n"
                        f"{indent}$__stmt->execute([{params_php}]);\n"
                        f"{indent}${result} = $__stmt;"
                    )
                    applied.append(
                        f"Replaced mysql_query() at line {j + 1} with a prepared "
                        f"statement (execute + bound params)."
                    )
                    break
        i += 1
    return "\n".join(lines), applied, []


# ---------------------------------------------------------------------------
# LL001 — remaining mysql_* function mapping (after LL002 pass)
# ---------------------------------------------------------------------------
_MYSQL_CONNECT_LINE = re.compile(r"^[ \t]*(?:\$\w+\s*=\s*)?mysql_connect\s*\([^;]*\)\s*;.*$", re.MULTILINE)
_MYSQL_SELECT_DB_LINE = re.compile(r"^[ \t]*mysql_select_db\s*\([^;]*\)\s*;.*$", re.MULTILINE)
_MYSQL_CLOSE_LINE = re.compile(r"^([ \t]*)mysql_close\s*\([^;]*\)\s*;", re.MULTILINE)
_MYSQL_QUERY_SIMPLE = re.compile(r'mysql_query\s*\(\s*("[^"]*"|\'[^\']*\'|\$\w+)\s*\)')
_MYSQL_FETCH_ASSOC = re.compile(r"mysql_fetch_assoc\s*\(\s*(\$\w+)\s*\)")
_MYSQL_FETCH_ARRAY = re.compile(r"mysql_fetch_array\s*\(\s*(\$\w+)\s*\)")
_MYSQL_FETCH_ROW = re.compile(r"mysql_fetch_row\s*\(\s*(\$\w+)\s*\)")
_MYSQL_FETCH_OBJECT = re.compile(r"mysql_fetch_object\s*\(\s*(\$\w+)\s*\)")
_MYSQL_NUM_ROWS = re.compile(r"mysql_num_rows\s*\(\s*(\$\w+)\s*\)")
_MYSQL_ESCAPE = re.compile(r"mysql_real_escape_string\s*\(\s*([^)]+)\)")
_MYSQL_ERROR = re.compile(r"mysql_error\s*\(\s*\)")
_MYSQL_INSERT_ID = re.compile(r"mysql_insert_id\s*\(\s*\)")
_MYSQL_AFFECTED = re.compile(r"mysql_affected_rows\s*\(\s*\)")


def fix_ll001_mysql_to_pdo(text: str) -> tuple[str, list[str], list[str]]:
    applied: list[str] = []
    original = text

    if _MYSQL_CONNECT_LINE.search(text) or _MYSQL_SELECT_DB_LINE.search(text):
        text = _MYSQL_CONNECT_LINE.sub("", text)
        text = _MYSQL_SELECT_DB_LINE.sub("", text)
        # Insert the PDO bootstrap right after the opening <?php tag.
        text = re.sub(
            r"^(<\?php\s*)",
            r"\1\nrequire_once __DIR__ . '/includes/db.php';\n$pdo = get_pdo();\n",
            text,
            count=1,
        )
        applied.append("Replaced mysql_connect()/mysql_select_db() with a shared PDO "
                        "connection from includes/db.php (get_pdo()).")

    text, n = _MYSQL_QUERY_SIMPLE.subn(r"$pdo->query(\1)", text)
    if n:
        applied.append(f"Rewrote {n} non-parameterized mysql_query() call(s) to $pdo->query().")

    text, n = _MYSQL_FETCH_ASSOC.subn(r"\1->fetch(PDO::FETCH_ASSOC)", text)
    if n:
        applied.append(f"Rewrote {n} mysql_fetch_assoc() call(s) to PDOStatement::fetch().")

    text, n = _MYSQL_FETCH_ARRAY.subn(r"\1->fetch(PDO::FETCH_BOTH)", text)
    if n:
        applied.append(f"Rewrote {n} mysql_fetch_array() call(s) to PDOStatement::fetch().")

    text, n = _MYSQL_FETCH_ROW.subn(r"\1->fetch(PDO::FETCH_NUM)", text)
    if n:
        applied.append(f"Rewrote {n} mysql_fetch_row() call(s) to PDOStatement::fetch().")

    text, n = _MYSQL_FETCH_OBJECT.subn(r"\1->fetch(PDO::FETCH_OBJ)", text)
    if n:
        applied.append(f"Rewrote {n} mysql_fetch_object() call(s) to PDOStatement::fetch().")

    text, n = _MYSQL_NUM_ROWS.subn(r"\1->rowCount()", text)
    if n:
        applied.append(f"Rewrote {n} mysql_num_rows() call(s) to PDOStatement::rowCount().")

    text, n = _MYSQL_ESCAPE.subn(
        r"\1  /* LegacyLift: escaping no longer needed — value is now bound via a "
        r"prepared statement parameter */",
        text,
    )
    if n:
        applied.append(f"Removed {n} now-unnecessary mysql_real_escape_string() call(s) "
                        f"(values are bound as prepared-statement parameters).")

    text, n = _MYSQL_ERROR.subn("implode(' ', $pdo->errorInfo())", text)
    if n:
        applied.append(f"Rewrote {n} mysql_error() call(s) to PDO::errorInfo().")

    text, n = _MYSQL_INSERT_ID.subn("$pdo->lastInsertId()", text)
    if n:
        applied.append(f"Rewrote {n} mysql_insert_id() call(s) to PDO::lastInsertId().")

    text, n = _MYSQL_AFFECTED.subn("$__stmt->rowCount()", text)
    if n:
        applied.append(f"Rewrote {n} mysql_affected_rows() call(s) to PDOStatement::rowCount().")

    text, n = _MYSQL_CLOSE_LINE.subn(
        r"\1// LegacyLift: mysql_close() removed — PDO connections close automatically.", text
    )
    if n:
        applied.append(f"Removed {n} mysql_close() call(s) — PDO closes on scope exit.")

    if text != original:
        text = re.sub(r"\n{3,}", "\n\n", text)
    return text, applied, []


# ---------------------------------------------------------------------------
# LL003 — output escaping
# ---------------------------------------------------------------------------
_ECHO_REQUEST = re.compile(r"\b(echo|print)\s+(\$_(?:GET|POST|REQUEST|COOKIE)\s*\[[^\]]+\])\s*;")
_SHORT_ECHO_REQUEST = re.compile(r"<\?=\s*(\$_(?:GET|POST|REQUEST|COOKIE)\s*\[[^\]]+\])\s*\?>")
_ECHO_PLAIN_VAR = re.compile(r"\b(echo|print)\s+(\$\w+)\s*;")
_SHORT_ECHO_PLAIN_VAR = re.compile(r"<\?=\s*(\$\w+)\s*\?>")


def fix_ll003_escape_output(text: str) -> tuple[str, list[str], list[str]]:
    applied: list[str] = []

    text, n = _SHORT_ECHO_REQUEST.subn(r"<?= e(\1) ?>", text)
    if n:
        applied.append(f"Wrapped {n} short-echo request-input output(s) with e() (htmlspecialchars).")

    text, n = _ECHO_REQUEST.subn(r"\1 e(\2);", text)
    if n:
        applied.append(f"Wrapped {n} echo/print of request input with e() (htmlspecialchars).")

    text, n = _SHORT_ECHO_PLAIN_VAR.subn(r"<?= e(\1) ?>", text)
    if n:
        applied.append(f"Wrapped {n} short-echo variable output(s) with e() (htmlspecialchars).")

    text, n = _ECHO_PLAIN_VAR.subn(r"\1 e(\2);", text)
    if n:
        applied.append(f"Wrapped {n} echo/print variable statement(s) with e() (htmlspecialchars).")

    if applied and "require_once __DIR__ . '/includes/escape.php';" not in text:
        text = re.sub(
            r"^(<\?php\s*)",
            r"\1\nrequire_once __DIR__ . '/includes/escape.php';\n",
            text,
            count=1,
        )
    return text, applied, []


# ---------------------------------------------------------------------------
# LL004 — weak password hashing → password_hash()/password_verify()
# ---------------------------------------------------------------------------
_MD5_HASH_ON_INSERT = re.compile(r"md5\s*\(\s*(\$_(?:POST|REQUEST)\[[^\]]+\]|\$\w+)\s*\)")
_LEGACY_COMPARE = re.compile(
    r"(?P<row>\$\w+\s*\[\s*['\"]password['\"]\s*\])\s*==\s*md5\s*\(\s*(?P<pw>\$_(?:POST|REQUEST)\[[^\]]+\]|\$\w+)\s*\)"
)


_SQL_CONTEXT_LINE = re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE|WHERE)\b|\$\w*sql\w*\s*=", re.IGNORECASE)


def fix_ll004_password_hash(text: str) -> tuple[str, list[str], list[str]]:
    applied: list[str] = []
    assisted: list[str] = []

    def repl_compare(m):
        applied.append("Replaced md5() password comparison with legacy_verify_password() "
                        "(verifies password_hash() format, or upgrades a legacy md5 hash "
                        "on successful login).")
        return f"legacy_verify_password({m.group('pw')}, {m.group('row')}, $pdo, $row['id'])"

    text = _LEGACY_COMPARE.sub(repl_compare, text)

    # Hashing on registration/insert (not already handled by the compare rewrite).
    # Guarded: never rewrite an md5() call that is still sitting inside a SQL
    # query string — password_hash() is salted/non-deterministic, so doing
    # that would silently break an equality match against a stored hash.
    def repl_hash(line_text: str) -> str:
        if "legacy_verify_password(" in line_text:
            return line_text
        if _SQL_CONTEXT_LINE.search(line_text):
            if _MD5_HASH_ON_INSERT.search(line_text):
                assisted.append(
                    "Left an md5() call inside a SQL query string untouched — rewriting it to "
                    "password_hash() would break the query (non-deterministic output). Move the "
                    "password check out of SQL and into legacy_verify_password() by hand."
                )
            return line_text

        def repl(m):
            applied.append("Replaced md5() password hashing with password_hash(..., PASSWORD_DEFAULT).")
            return f"password_hash({m.group(1)}, PASSWORD_DEFAULT)"

        return _MD5_HASH_ON_INSERT.sub(repl, line_text)

    text = "\n".join(repl_hash(line) for line in text.split("\n"))

    if applied and "require_once __DIR__ . '/includes/auth.php';" not in text:
        text = re.sub(
            r"^(<\?php\s*)",
            r"\1\nrequire_once __DIR__ . '/includes/auth.php';\n",
            text,
            count=1,
        )
    return text, applied, assisted


# ---------------------------------------------------------------------------
# LL005 — CSRF: inject token field into POST forms, verify in POST handlers
# ---------------------------------------------------------------------------
_FORM_POST_TAG = re.compile(r"(<form[^>]+method=[\"']?post[^>]*>)", re.IGNORECASE)
_CSRF_FIELD_PRESENT = re.compile(r"csrf_token", re.IGNORECASE)
_POST_HANDLER_IF = re.compile(
    r"(if\s*\([^{\n]*\$_SERVER\[.REQUEST_METHOD.\][^{\n]*==\s*[\"']POST[\"'][^{\n]*\)\s*\{)"
)


def fix_ll005_csrf(text: str) -> tuple[str, list[str], list[str]]:
    applied: list[str] = []

    def repl_form(m):
        return m.group(1) + '\n    <input type="hidden" name="csrf_token" value="<?= csrf_token() ?>">'

    if _FORM_POST_TAG.search(text) and not _CSRF_FIELD_PRESENT.search(text):
        text, n = _FORM_POST_TAG.subn(repl_form, text)
        if n:
            applied.append(f"Injected a csrf_token hidden field into {n} POST form(s).")

    def repl_handler(m):
        return m.group(1) + (
            "\n    if (!csrf_verify($_POST['csrf_token'] ?? '')) { "
            "http_response_code(403); die('Invalid CSRF token'); }"
        )

    if _POST_HANDLER_IF.search(text) and "csrf_verify(" not in text:
        text, n = _POST_HANDLER_IF.subn(repl_handler, text)
        if n:
            applied.append(f"Injected csrf_verify() check into {n} POST handler(s).")

    if applied and "require_once __DIR__ . '/includes/csrf.php';" not in text:
        text = re.sub(
            r"^(<\?php\s*)",
            r"\1\nrequire_once __DIR__ . '/includes/csrf.php';\n",
            text,
            count=1,
        )
    return text, applied, []


# ---------------------------------------------------------------------------
# LL006 — register_globals-style extract()/$HTTP_*_VARS: flag, don't rewrite
# (removing extract() safely requires knowing every variable name it
# produces and how each is used downstream — not provably safe to automate).
# ---------------------------------------------------------------------------
_EXTRACT_REQUEST_LINE = re.compile(
    r"^([ \t]*)(extract\s*\(\s*\$_(?:GET|POST|REQUEST|COOKIE)\b[^;]*;)", re.MULTILINE
)
_OLD_SUPERGLOBAL_LINE = re.compile(
    r"^([ \t]*)(.*\$HTTP_(?:GET|POST|COOKIE)_VARS\b.*;)", re.MULTILINE
)


def fix_ll006_flag_extract(text: str) -> tuple[str, list[str], list[str]]:
    assisted: list[str] = []
    already_flagged = "TODO LegacyLift: extract()" in text or "TODO LegacyLift: legacy superglobal" in text

    def repl_extract(m):
        assisted.append("Flagged extract() on a request superglobal — replacing it safely "
                         "requires knowing every variable name it produces and how each is "
                         "used afterward, so it is left for manual review.")
        return f"{m.group(1)}// TODO LegacyLift: extract() recreates register_globals — " \
               f"replace with explicit $_REQUEST['key'] reads.\n{m.group(1)}{m.group(2)}"

    def repl_superglobal(m):
        assisted.append("Flagged a removed $HTTP_*_VARS superglobal reference for manual "
                         "replacement with $_GET/$_POST/$_COOKIE.")
        return f"{m.group(1)}// TODO LegacyLift: legacy superglobal, replace with " \
               f"$_GET/$_POST/$_COOKIE.\n{m.group(1)}{m.group(2)}"

    if not already_flagged:
        text = _EXTRACT_REQUEST_LINE.sub(repl_extract, text)
        text = _OLD_SUPERGLOBAL_LINE.sub(repl_superglobal, text)
    return text, [], assisted


# ---------------------------------------------------------------------------
# LL007 — deprecated functions
# ---------------------------------------------------------------------------
_SPLIT_CALL = re.compile(r"\bsplit\s*\(\s*(['\"][^'\"]+['\"])\s*,\s*")
_EREG_CALL = re.compile(r"\beregi?\s*\(\s*(['\"])([^'\"]+)\1\s*,\s*")
_MAGIC_QUOTES_IF = re.compile(
    r"if\s*\(\s*(?:function_exists\(['\"]get_magic_quotes_gpc['\"]\)\s*&&\s*)?"
    r"get_magic_quotes_gpc\s*\(\s*\)\s*\)\s*\{[^}]*\}", re.DOTALL
)


def fix_ll007_deprecated(text: str) -> tuple[str, list[str], list[str]]:
    applied: list[str] = []

    text, n = _SPLIT_CALL.subn(r"explode(\1, ", text)
    if n:
        applied.append(f"Replaced {n} split() call(s) with explode() (literal-delimiter form).")

    def repl_ereg(m):
        return f"preg_match('/{m.group(2)}/', "

    text, n = _EREG_CALL.subn(repl_ereg, text)
    if n:
        applied.append(f"Replaced {n} ereg()/eregi() call(s) with preg_match().")

    text, n = _MAGIC_QUOTES_IF.subn(
        "// LegacyLift: magic_quotes_gpc was removed in PHP 5.4 — obsolete guard deleted.", text
    )
    if n:
        applied.append(f"Removed {n} obsolete magic_quotes_gpc guard block(s).")

    return text, applied, []


# ---------------------------------------------------------------------------
# LL008 — short tags (mechanical, safe); @ / error_reporting(0) → ASSISTED
# ---------------------------------------------------------------------------
_SHORT_TAG_OPEN = re.compile(r"^(\s*)<\?(?!php|=|xml)", re.MULTILINE)
_ERROR_SUPPRESS = re.compile(r"(=\s*)@(\w+\s*\()")
_ERROR_REPORTING_OFF = re.compile(r"error_reporting\s*\(\s*0\s*\)\s*;")


def fix_ll008_short_tags(text: str) -> tuple[str, list[str], list[str]]:
    applied: list[str] = []
    assisted: list[str] = []

    text, n = _SHORT_TAG_OPEN.subn(r"\1<?php", text)
    if n:
        applied.append(f"Converted {n} short open tag(s) `<?` to `<?php`.")

    for m in _ERROR_SUPPRESS.finditer(text):
        assisted.append(
            f"`@{m.group(2)}` error suppression left in place — silencing errors changes "
            f"behaviour and needs a human to decide on explicit error handling."
        )

    if _ERROR_REPORTING_OFF.search(text):
        assisted.append("error_reporting(0) left in place — flip to E_ALL only after "
                         "confirming no code relies on warnings being hidden.")

    return text, applied, assisted


# ---------------------------------------------------------------------------
# LL011 — hard-coded credentials → getenv()
# ---------------------------------------------------------------------------
_HARDCODED_ASSIGN = re.compile(
    r"\$(db_password|db_user|db_host|db_name|api_key|secret)\s*=\s*[\"']([^\"']*)[\"']\s*;",
    re.IGNORECASE,
)


def fix_ll011_env_secrets(text: str) -> tuple[str, list[str], list[str], dict[str, str]]:
    applied: list[str] = []
    env_keys: dict[str, str] = {}

    def repl(m):
        name = m.group(1)
        env_key = name.upper()
        env_keys[env_key] = m.group(2)
        applied.append(f"Moved hard-coded `${name}` to environment variable {env_key} "
                        f"(loaded via getenv()).")
        return f"${name} = getenv('{env_key}');"

    text = _HARDCODED_ASSIGN.sub(repl, text)
    if applied and "require_once __DIR__ . '/includes/env.php';" not in text:
        text = re.sub(
            r"^(<\?php\s*)",
            r"\1\nrequire_once __DIR__ . '/includes/env.php';\n",
            text,
            count=1,
        )
    return text, applied, [], env_keys


# ---------------------------------------------------------------------------
# LL013 — session fixation: insert session_regenerate_id after login
# ---------------------------------------------------------------------------
_SESSION_LOGIN_SET = re.compile(
    r"^([ \t]*)(\$_SESSION\[['\"](?:user_id|username|logged_in|admin)['\"]\]\s*=[^;]+;)",
    re.MULTILINE,
)


def fix_ll013_session_regen(text: str) -> tuple[str, list[str], list[str]]:
    applied: list[str] = []
    if "session_regenerate_id(" in text:
        return text, applied, []

    def repl(m):
        applied.append(f"Inserted session_regenerate_id(true) before session login data "
                        f"is set (line {text[:m.start()].count(chr(10)) + 1}).")
        return f"{m.group(1)}session_regenerate_id(true);\n{m.group(1)}{m.group(2)}"

    new_text, n = _SESSION_LOGIN_SET.subn(repl, text, count=1)
    return new_text, applied, []
