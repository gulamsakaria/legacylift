"""Detection rules LL001–LL014.

Each rule is a small, independently testable function:

    def detect(lines: list[str], filepath: Path, is_template: bool) -> list[Hit]

A ``Hit`` is (line_no, snippet, explanation). Rules operate line-by-line on
purpose: it keeps every rule auditable in a code review and keeps the tool
dependency-free and fast on codebases with no PHP toolchain available. To
control false positives, every rule skips comment-only lines and lines that
are already wrapped in the project's recognised "safe" helpers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

Hit = tuple[int, str, str]


@dataclass(frozen=True)
class Rule:
    id: str
    severity: str  # critical | high | medium | low
    title: str
    fixable: bool
    detect: "callable"


def _is_comment(line: str) -> bool:
    s = line.strip()
    return s.startswith("//") or s.startswith("#") or s.startswith("*") or s.startswith("/*")


def _snippet(line: str, limit: int = 110) -> str:
    s = line.strip()
    return s if len(s) <= limit else s[: limit - 1] + "…"


# ---------------------------------------------------------------------------
# LL001 — removed mysql_* functions
# ---------------------------------------------------------------------------
_MYSQL_FUNCS = re.compile(
    r"\bmysql_(connect|query|fetch_assoc|fetch_array|fetch_row|fetch_object|"
    r"real_escape_string|num_rows|close|select_db|error|insert_id|affected_rows)\s*\("
)


def detect_ll001(lines, filepath, is_template):
    hits = []
    for i, line in enumerate(lines, 1):
        if _is_comment(line):
            continue
        m = _MYSQL_FUNCS.search(line)
        if m:
            hits.append(
                (i, _snippet(line), f"Removed PHP 7+ function `{m.group(0).rstrip('(')}` — "
                                     "replace with a PDO equivalent.")
            )
    return hits


# ---------------------------------------------------------------------------
# LL002 — SQL injection via string concatenation with request input
# ---------------------------------------------------------------------------
_SQL_KEYWORD = re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE)\b", re.IGNORECASE)
_REQUEST_INPUT = re.compile(r"\$_(GET|POST|REQUEST|COOKIE)\s*\[")
_CONCAT_HINT = re.compile(r"[\"'].*\.\s*\$|\$\w[\w\[\]'\"]*\s*\.\s*[\"']")
_INTERP_IN_STRING = re.compile(r"[\"'][^\"']*\$_(GET|POST|REQUEST|COOKIE)\s*\[")


def detect_ll002(lines, filepath, is_template):
    hits = []
    for i, line in enumerate(lines, 1):
        if _is_comment(line):
            continue
        if "prepare(" in line or "bindParam" in line or "bindValue" in line:
            continue
        if not _SQL_KEYWORD.search(line):
            continue
        if _REQUEST_INPUT.search(line) and (_CONCAT_HINT.search(line) or _INTERP_IN_STRING.search(line)):
            hits.append(
                (i, _snippet(line),
                 "SQL query built by concatenating/interpolating request input directly — "
                 "classic SQL injection. Use a parameterised PDO query instead.")
            )
    return hits


# ---------------------------------------------------------------------------
# LL003 — unescaped output of user input (XSS)
# ---------------------------------------------------------------------------
_ECHO_REQUEST = re.compile(r"\b(echo|print)\s+\$_(GET|POST|REQUEST|COOKIE)\s*\[")
_SHORT_ECHO_REQUEST = re.compile(r"<\?=\s*\$_(GET|POST|REQUEST|COOKIE)\s*\[")
_ECHO_VAR = re.compile(r"\b(echo|print)\s+\$(\w+)\s*;")
_SHORT_ECHO_VAR = re.compile(r"<\?=\s*\$(\w+)\s*\?>")


def detect_ll003(lines, filepath, is_template):
    hits = []
    for i, line in enumerate(lines, 1):
        if _is_comment(line):
            continue
        if "htmlspecialchars" in line or line.strip().startswith("function ") or " e(" in line or "e($" in line:
            continue
        if _ECHO_REQUEST.search(line) or _SHORT_ECHO_REQUEST.search(line):
            hits.append(
                (i, _snippet(line),
                 "Request input echoed directly without `htmlspecialchars()` — reflected XSS.")
            )
            continue
        # echoing a plain variable in a template context without the safe helper
        if is_template and (_ECHO_VAR.search(line) or _SHORT_ECHO_VAR.search(line)):
            if "htmlspecialchars" not in line:
                hits.append(
                    (i, _snippet(line),
                     "Variable echoed into HTML without escaping — potential stored/reflected XSS "
                     "if the value ever contains user-controlled data.")
                )
    return hits


# ---------------------------------------------------------------------------
# LL004 — weak password hashing
# ---------------------------------------------------------------------------
_WEAK_HASH_COMPARE = re.compile(
    r"\$\w+\[\s*['\"]password['\"]\s*\]\s*==\s*(md5|sha1)\s*\(", re.IGNORECASE
)
_WEAK_HASH_CALL = re.compile(
    r"\b(md5|sha1)\s*\(\s*(\$_(?:POST|REQUEST)\[['\"]?\w*pass\w*['\"]?\]|\$\w*pass\w*)\s*\)",
    re.IGNORECASE,
)
_PLAINTEXT_COMPARE = re.compile(r"\$\w*password\w*\s*==\s*\$_(GET|POST|REQUEST)", re.IGNORECASE)


def detect_ll004(lines, filepath, is_template):
    hits = []
    for i, line in enumerate(lines, 1):
        if _is_comment(line):
            continue
        if "password_hash" in line or "password_verify" in line:
            continue
        if _WEAK_HASH_COMPARE.search(line) or _WEAK_HASH_CALL.search(line):
            hits.append((i, _snippet(line), "Password hashed or compared with md5()/sha1() — "
                                             "trivially crackable. Use password_hash()/"
                                             "password_verify()."))
        elif _PLAINTEXT_COMPARE.search(line):
            hits.append((i, _snippet(line), "Password compared in plaintext against raw request "
                                             "input — store and verify with password_hash()."))
    return hits


# ---------------------------------------------------------------------------
# LL005 — missing CSRF token on state-changing POST forms/handlers
# ---------------------------------------------------------------------------
_FORM_POST = re.compile(r"<form[^>]+method=[\"']?post", re.IGNORECASE)
_CSRF_TOKEN_FIELD = re.compile(r"csrf_token|_token", re.IGNORECASE)
_POST_HANDLER = re.compile(r"\$_SERVER\[.REQUEST_METHOD.\]\s*==\s*[\"']POST[\"']")
_CSRF_CHECK_CALL = re.compile(r"csrf_verify|verify_csrf|check_csrf", re.IGNORECASE)


def detect_ll005_forms(lines, filepath, is_template):
    """Flag <form method=post> blocks (within a small window) with no CSRF field."""
    hits = []
    n = len(lines)
    for i, line in enumerate(lines, 1):
        if _FORM_POST.search(line):
            window = "\n".join(lines[i - 1: min(i + 25, n)])
            if not _CSRF_TOKEN_FIELD.search(window):
                hits.append((i, _snippet(line), "POST form has no CSRF token field — "
                                                 "state-changing request forgeable cross-site."))
    return hits


def detect_ll005_handlers(lines, filepath, is_template):
    hits = []
    n = len(lines)
    for i, line in enumerate(lines, 1):
        if _POST_HANDLER.search(line):
            window = "\n".join(lines[i - 1: min(i + 15, n)])
            if not _CSRF_CHECK_CALL.search(window):
                hits.append((i, _snippet(line), "POST handler performs a state change with no "
                                                 "CSRF token verification call."))
    return hits


def detect_ll005(lines, filepath, is_template):
    return detect_ll005_forms(lines, filepath, is_template) + detect_ll005_handlers(
        lines, filepath, is_template
    )


# ---------------------------------------------------------------------------
# LL006 — register_globals-style / extract($_REQUEST) / $HTTP_*_VARS
# ---------------------------------------------------------------------------
_EXTRACT_REQUEST = re.compile(r"\bextract\s*\(\s*\$_(GET|POST|REQUEST|COOKIE)\b")
_OLD_SUPERGLOBAL = re.compile(r"\$HTTP_(GET|POST|COOKIE)_VARS\b")


def detect_ll006(lines, filepath, is_template):
    hits = []
    for i, line in enumerate(lines, 1):
        if _is_comment(line):
            continue
        if _EXTRACT_REQUEST.search(line):
            hits.append((i, _snippet(line), "extract() on request superglobal recreates "
                                             "register_globals — arbitrary variable injection."))
        elif _OLD_SUPERGLOBAL.search(line):
            hits.append((i, _snippet(line), "Removed PHP 5.4-era superglobal "
                                             "($HTTP_*_VARS) — use $_GET/$_POST/$_COOKIE."))
    return hits


# ---------------------------------------------------------------------------
# LL007 — deprecated/removed functions
# ---------------------------------------------------------------------------
_DEPRECATED_FUNCS = re.compile(
    r"\b(ereg|eregi|ereg_replace|split|each|create_function)\s*\(|"
    r"\bmagic_quotes_gpc\s*\(|get_magic_quotes_gpc\s*\("
)


def detect_ll007(lines, filepath, is_template):
    hits = []
    for i, line in enumerate(lines, 1):
        if _is_comment(line):
            continue
        m = _DEPRECATED_FUNCS.search(line)
        if m:
            hits.append((i, _snippet(line), f"Deprecated/removed function `{m.group(0).rstrip('(')}` "
                                             "has no direct PHP 8 equivalent as written."))
    return hits


# ---------------------------------------------------------------------------
# LL008 — short open tags, @ suppression abuse, error display in prod
# ---------------------------------------------------------------------------
_SHORT_TAG = re.compile(r"^\s*<\?(?!php|=|xml)")
_ERROR_SUPPRESS = re.compile(r"=\s*@\w+\s*\(|^\s*@\w+\s*\(")
_DISPLAY_ERRORS_ON = re.compile(r"display_errors.{0,10}(1|On|on|true)")
_ERROR_REPORTING_OFF = re.compile(r"error_reporting\s*\(\s*0\s*\)")


def detect_ll008(lines, filepath, is_template):
    hits = []
    for i, line in enumerate(lines, 1):
        if _is_comment(line):
            continue
        if _SHORT_TAG.match(line):
            hits.append((i, _snippet(line), "Short open tag `<?` — removed by default since "
                                             "PHP 7; use full `<?php`."))
        if _ERROR_SUPPRESS.search(line):
            hits.append((i, _snippet(line), "`@` error suppression hides failures silently — "
                                             "handle the error explicitly instead."))
        if _ERROR_REPORTING_OFF.search(line):
            hits.append((i, _snippet(line), "error_reporting(0) hides all errors, including "
                                             "ones that indicate security bugs."))
        if _DISPLAY_ERRORS_ON.search(line) and "ini_set" in line:
            hits.append((i, _snippet(line), "display_errors enabled — leaks stack traces/paths "
                                             "to attackers in production."))
    return hits


# ---------------------------------------------------------------------------
# LL009 — dangerous functions: eval, exec family, include/require w/ user path
# ---------------------------------------------------------------------------
_EVAL_CALL = re.compile(r"\beval\s*\(")
_EXEC_FAMILY = re.compile(r"\b(exec|system|shell_exec|passthru|popen|proc_open)\s*\(\s*[^)]*\$")
_DYNAMIC_INCLUDE = re.compile(
    r"\b(include|include_once|require|require_once)\s*\(?\s*[^;]*\$_(GET|POST|REQUEST|COOKIE)"
)


def detect_ll009(lines, filepath, is_template):
    hits = []
    for i, line in enumerate(lines, 1):
        if _is_comment(line):
            continue
        if _EVAL_CALL.search(line):
            hits.append((i, _snippet(line), "eval() on any dynamic input is arbitrary code "
                                             "execution — remove or replace entirely."))
        elif _EXEC_FAMILY.search(line):
            hits.append((i, _snippet(line), "Shell command built with a variable — command "
                                             "injection risk."))
        elif _DYNAMIC_INCLUDE.search(line):
            hits.append((i, _snippet(line), "include/require path built from request input — "
                                             "local/remote file inclusion (LFI/RFI)."))
    return hits


# ---------------------------------------------------------------------------
# LL010 — file upload handling without validation
# ---------------------------------------------------------------------------
_FILE_UPLOAD_MOVE = re.compile(r"move_uploaded_file\s*\(")
_MIME_OR_EXT_CHECK = re.compile(r"getimagesize|finfo_file|mime_content_type|pathinfo.*PATHINFO_EXTENSION|"
                                 r"in_array\s*\(\s*\$\w*ext", re.IGNORECASE)


def detect_ll010(lines, filepath, is_template):
    hits = []
    n = len(lines)
    for i, line in enumerate(lines, 1):
        if _FILE_UPLOAD_MOVE.search(line):
            window = "\n".join(lines[max(0, i - 15): i])
            if not _MIME_OR_EXT_CHECK.search(window):
                hits.append((i, _snippet(line), "File upload moved into place with no "
                                                 "extension/MIME/size validation beforehand — "
                                                 "arbitrary file upload risk."))
    return hits


# ---------------------------------------------------------------------------
# LL011 — hard-coded credentials
# ---------------------------------------------------------------------------
_HARDCODED_CRED = re.compile(
    r"(\$(?:db_)?password|\$db_pass|\$api_key|\$secret)\s*=\s*[\"'][^\"']{3,}[\"']",
    re.IGNORECASE,
)
_MYSQL_CONNECT_LITERAL = re.compile(
    r"mysql_connect\s*\(\s*[\"'][^\"']+[\"']\s*,\s*[\"'][^\"']+[\"']\s*,\s*[\"'][^\"']+[\"']"
)


def detect_ll011(lines, filepath, is_template):
    hits = []
    for i, line in enumerate(lines, 1):
        if _is_comment(line):
            continue
        if "getenv(" in line or "$_ENV" in line:
            continue
        if _HARDCODED_CRED.search(line) or _MYSQL_CONNECT_LITERAL.search(line):
            hits.append((i, _snippet(line), "Credential hard-coded in source — move to `.env` "
                                             "and load via getenv()."))
    return hits


# ---------------------------------------------------------------------------
# LL012 — mixed HTML + business logic (metric-based, file-level)
# ---------------------------------------------------------------------------
_LOGIC_LINE = re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE|mysql_query)\b|->query|->prepare", re.IGNORECASE)
_HTML_LINE = re.compile(r"<(html|body|table|div|form|tr|td)\b", re.IGNORECASE)


def detect_ll012(lines, filepath, is_template):
    logic = sum(1 for line in lines if _LOGIC_LINE.search(line))
    html = sum(1 for line in lines if _HTML_LINE.search(line))
    if logic >= 3 and html >= 3:
        ratio = logic / max(1, logic + html)
        return [(1, f"{logic} SQL/logic lines mixed with {html} HTML-structure lines in one file",
                 f"Business logic and presentation are interleaved (logic ratio {ratio:.2f}) — "
                 "separate the query/handler code from the HTML template.")]
    return []


# ---------------------------------------------------------------------------
# LL013 — missing session hardening
# ---------------------------------------------------------------------------
_LOGIN_SUCCESS = re.compile(r"\$_SESSION\[.(user_id|username|logged_in|admin).\]\s*=", re.IGNORECASE)
_REGEN_ID = re.compile(r"session_regenerate_id\s*\(")
_SESSION_START = re.compile(r"session_start\s*\(\s*\)\s*;")


def detect_ll013(lines, filepath, is_template):
    hits = []
    n = len(lines)
    for i, line in enumerate(lines, 1):
        if _LOGIN_SUCCESS.search(line):
            window = "\n".join(lines[max(0, i - 10): i])
            if not _REGEN_ID.search(window):
                hits.append((i, _snippet(line), "Session established on login without "
                                                 "session_regenerate_id() — session fixation risk."))
    return hits


# ---------------------------------------------------------------------------
# LL014 — old-style class constructors / missing visibility
# ---------------------------------------------------------------------------
_CLASS_DEF = re.compile(r"\bclass\s+(\w+)")
_OLD_CTOR = re.compile(r"function\s+(\w+)\s*\(")
_BARE_VAR = re.compile(r"^\s*var\s+\$\w+")
_UNTYPED_PROP = re.compile(r"^\s*(public|private|protected)?\s*\$\w+\s*;")
_VISIBILITY = re.compile(r"^\s*(public|private|protected)\s+function\s+\w+\s*\(")
_FUNCTION_DEF = re.compile(r"^\s*function\s+(\w+)\s*\(")


def detect_ll014(lines, filepath, is_template):
    hits = []
    current_class = None
    for i, line in enumerate(lines, 1):
        cm = _CLASS_DEF.search(line)
        if cm:
            current_class = cm.group(1)
        if _is_comment(line):
            continue
        if current_class:
            om = _OLD_CTOR.search(line)
            if om and om.group(1) == current_class:
                hits.append((i, _snippet(line), f"Old-style constructor `{current_class}()` named "
                                                 "after the class — use __construct()."))
            fm = _FUNCTION_DEF.match(line)
            if fm and not _VISIBILITY.match(line) and fm.group(1) != "__construct":
                hits.append((i, _snippet(line), f"Method `{fm.group(1)}()` declared without a "
                                                 "visibility keyword (public/private/protected)."))
        if _BARE_VAR.match(line):
            hits.append((i, _snippet(line), "Old-style `var $prop;` property declaration — "
                                             "use a visibility keyword."))
    return hits


# ---------------------------------------------------------------------------
# LL015 — unserialize() on request input (PHP object injection)
# ---------------------------------------------------------------------------
_UNSERIALIZE_REQUEST = re.compile(
    r"\bunserialize\s*\(\s*\$_(GET|POST|REQUEST|COOKIE)\s*\["
)
_UNSERIALIZE_VAR_FROM_REQUEST = re.compile(
    r"\bunserialize\s*\(\s*\$\w+"
)


def detect_ll015(lines, filepath, is_template):
    """Flag unserialize() called directly on a request superglobal.

    PHP's unserialize() on attacker-controlled data allows PHP object injection
    — an attacker can craft a serialized payload that instantiates arbitrary
    classes and triggers their __wakeup/__destruct magic methods, leading to
    remote code execution or privilege escalation.

    False-positive guard: skip lines that are comments, and only flag the
    direct-call form (unserialize($_GET[...]) etc.) to keep precision high.
    A variable-indirection form (unserialize($var) where $var came from a
    request) is a known false-negative; it is intentionally not flagged here
    to avoid excessive noise — the direct form is the most common and clear-
    cut case.
    """
    hits = []
    for i, line in enumerate(lines, 1):
        if _is_comment(line):
            continue
        if _UNSERIALIZE_REQUEST.search(line):
            hits.append(
                (i, _snippet(line),
                 "unserialize() called directly on request input — PHP object injection: "
                 "an attacker can craft a payload that triggers arbitrary magic-method "
                 "execution (__wakeup/__destruct). Use json_decode() or a safe "
                 "allow-listed deserializer instead.")
            )
    return hits


# ---------------------------------------------------------------------------
# LL016 — predictable random used for security-sensitive token generation
# ---------------------------------------------------------------------------
_WEAK_RAND_CALL = re.compile(r"\b(rand|mt_rand)\s*\(")
_TOKEN_VAR = re.compile(
    r"\$\w*(?:token|csrf|nonce|secret|session_?id|key)\w*\s*=",
    re.IGNORECASE,
)
_SESSION_WRITE = re.compile(r"\$_SESSION\s*\[")


def detect_ll016(lines, filepath, is_template):
    """Flag rand()/mt_rand() used to produce a security-sensitive token.

    rand() and mt_rand() are seeded from a predictable state and must never
    be used for CSRF tokens, session IDs, password-reset nonces, or any other
    value whose unpredictability is a security requirement. Use
    random_bytes(N) / bin2hex(random_bytes(N)) instead (PHP 7+).

    Detection strategy: flag a line that calls rand()/mt_rand() when the
    assignment target looks like a token/key/nonce variable name, OR when
    a rand()/mt_rand() call appears on the same line as a $_SESSION write
    (a common pattern for session-fixation-adjacent token generation).

    False-positive guard: skip comment lines; skip lines that already use
    random_bytes or openssl_random_pseudo_bytes, which are the correct
    alternatives.
    """
    hits = []
    for i, line in enumerate(lines, 1):
        if _is_comment(line):
            continue
        if "random_bytes" in line or "openssl_random_pseudo_bytes" in line:
            continue
        if not _WEAK_RAND_CALL.search(line):
            continue
        if _TOKEN_VAR.search(line) or _SESSION_WRITE.search(line):
            hits.append(
                (i, _snippet(line),
                 "rand()/mt_rand() is not cryptographically secure and must not be used "
                 "to generate tokens, nonces, CSRF values, or session identifiers — "
                 "use random_bytes()/bin2hex() (PHP 7+) instead.")
            )
    return hits


RULES: list[Rule] = [
    Rule("LL001", "critical", "Removed mysql_* functions", True, detect_ll001),
    Rule("LL002", "critical", "SQL injection via string concatenation", True, detect_ll002),
    Rule("LL003", "high", "Unescaped output of user input (XSS)", True, detect_ll003),
    Rule("LL004", "critical", "Weak password hashing", True, detect_ll004),
    Rule("LL005", "high", "Missing CSRF protection", True, detect_ll005),
    Rule("LL006", "high", "register_globals-style superglobal use", False, detect_ll006),
    Rule("LL007", "medium", "Deprecated/removed functions", True, detect_ll007),
    Rule("LL008", "medium", "Short tags / error suppression abuse", True, detect_ll008),
    Rule("LL009", "critical", "Dangerous functions (eval/exec/LFI-RFI)", False, detect_ll009),
    Rule("LL010", "high", "Unvalidated file upload handling", False, detect_ll010),
    Rule("LL011", "high", "Hard-coded credentials", True, detect_ll011),
    Rule("LL012", "low", "Mixed HTML + business logic", False, detect_ll012),
    Rule("LL013", "medium", "Missing session hardening", True, detect_ll013),
    Rule("LL014", "low", "Old-style constructors / missing visibility", False, detect_ll014),
    Rule("LL015", "critical", "unserialize() on request input (object injection)", False, detect_ll015),
    Rule("LL016", "high", "Predictable rand()/mt_rand() used for token generation", False, detect_ll016),
]

RULES_BY_ID = {r.id: r for r in RULES}
