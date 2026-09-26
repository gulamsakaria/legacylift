"""Tests for the atomic fix functions, the SQL parameterization parser,
and idempotency of the full fix chain."""

from legacylift.fixer import fixes
from legacylift.fixer.engine import _apply_fix_chain


def test_split_top_level_concat_respects_quotes():
    expr = "\"a.b\" . $x . 'c.d'"
    parts = fixes.split_top_level_concat(expr)
    assert [p.strip() for p in parts] == ['"a.b"', "$x", "'c.d'"]


def test_parameterize_query_simple():
    expr = "\"SELECT * FROM t WHERE id = '\" . $_GET['id'] . \"'\""
    query, params = fixes.parameterize_query(expr)
    assert query == "SELECT * FROM t WHERE id = ?"
    assert params == ["$_GET['id']"]


def test_parameterize_query_multiple_params():
    expr = (
        "\"SELECT * FROM users WHERE username = '\" . $_POST['username'] . "
        "\"' AND password = '\" . md5($_POST['password']) . \"'\""
    )
    query, params = fixes.parameterize_query(expr)
    assert query == "SELECT * FROM users WHERE username = ? AND password = ?"
    assert params == ["$_POST['username']", "md5($_POST['password'])"]


def test_fix_ll001_mysql_to_pdo_rewrites_calls():
    code = (
        "<?php\n"
        "$conn = mysql_connect('h','u','p');\n"
        "mysql_select_db('db');\n"
        "$r = mysql_query('SELECT 1');\n"
        "$row = mysql_fetch_assoc($r);\n"
    )
    new_text, applied, assisted = fixes.fix_ll001_mysql_to_pdo(code)
    assert "mysql_connect" not in new_text
    assert "mysql_fetch_assoc" not in new_text
    assert "get_pdo()" in new_text
    assert "PDO::FETCH_ASSOC" in new_text
    assert applied


def test_fix_ll001_mysql_query_with_string_literal_argument():
    code = "<?php\n$r = mysql_query(\"SELECT COUNT(*) FROM students\");\n"
    new_text, applied, assisted = fixes.fix_ll001_mysql_to_pdo(code)
    assert "mysql_query" not in new_text
    assert '$pdo->query("SELECT COUNT(*) FROM students")' in new_text
    assert applied


def test_fix_ll004_does_not_touch_md5_inside_sql_string():
    code = "<?php\n$sql = \"SELECT * FROM t WHERE p = '\" . md5($_POST['p']) . \"'\";\n"
    new_text, applied, assisted = fixes.fix_ll004_password_hash(code)
    assert "md5(" in new_text  # left untouched — would break the query otherwise
    assert not applied
    assert assisted


def test_fix_ll004_rewrites_compare_pattern():
    code = "<?php\nif ($row['password'] == md5($_POST['password'])) { ok(); }\n"
    new_text, applied, assisted = fixes.fix_ll004_password_hash(code)
    assert "legacy_verify_password(" in new_text
    assert applied


def test_fix_chain_is_idempotent():
    code = (
        "<?php\n"
        "$conn = mysql_connect('h','u','p');\n"
        "mysql_select_db('db');\n"
        "$sql = \"SELECT * FROM users WHERE username = '\" . $_POST['username'] . \"'\";\n"
        "$r = mysql_query($sql);\n"
        "$row = mysql_fetch_assoc($r);\n"
        "if ($row['password'] == md5($_POST['password'])) { echo $_GET['x']; }\n"
    )
    once, _, _, _ = _apply_fix_chain(code)
    twice, applied2, _, _ = _apply_fix_chain(once)
    assert once == twice
    assert applied2 == {}


def test_fix_ll006_flags_extract_with_todo_comment():
    code = "<?php\nextract($_REQUEST);\n$x = 1;\n"
    new_text, applied, assisted = fixes.fix_ll006_flag_extract(code)
    assert "TODO LegacyLift: extract()" in new_text
    assert "extract($_REQUEST);" in new_text  # behavior untouched
    assert assisted
    assert not applied


def test_fix_ll005_handler_with_extra_conditions_gets_csrf_check():
    code = (
        "<?php\n"
        "if ($_SERVER['REQUEST_METHOD'] == 'POST' && isset($_POST['action']) "
        "&& $_POST['action'] == 'create') {\n"
        "  doStuff();\n"
        "}\n"
    )
    new_text, applied, _ = fixes.fix_ll005_csrf(code)
    assert "csrf_verify(" in new_text
    assert applied

    code = '<?php\n?>\n<form method="POST" action="x.php">\n<input name="a">\n</form>\n'
    new_text, applied, _ = fixes.fix_ll005_csrf(code)
    assert new_text.count("csrf_token()") == 1
    new_text2, applied2, _ = fixes.fix_ll005_csrf(new_text)
    assert new_text2 == new_text
    assert applied2 == []
