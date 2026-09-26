"""Positive and negative fixtures for every LLxxx rule — guards against
both false negatives (missed detections) and false positives."""

from pathlib import Path

import pytest

from legacylift.scanner.rules import RULES_BY_ID


def _hits(rule_id: str, code: str, filename: str = "test.php"):
    rule = RULES_BY_ID[rule_id]
    lines = code.split("\n")
    is_template = filename.endswith(".phtml")
    return rule.detect(lines, Path(filename), is_template)


@pytest.mark.parametrize(
    "rule_id,positive,negative",
    [
        ("LL001", "$r = mysql_query($sql);", "$r = $pdo->query($sql);"),
        (
            "LL002",
            "$sql = \"SELECT * FROM t WHERE id = '\" . $_GET['id'] . \"'\";",
            "$stmt = $pdo->prepare('SELECT * FROM t WHERE id = ?'); $stmt->execute([$_GET['id']]);",
        ),
        ("LL003", "echo $_GET['name'];", "echo htmlspecialchars($_GET['name']);"),
        ("LL004", "$h = md5($password);", "$h = password_hash($password, PASSWORD_DEFAULT);"),
        (
            "LL006",
            "extract($_REQUEST);",
            "$username = $_REQUEST['username'];",
        ),
        ("LL007", "$parts = split(',', $s);", "$parts = explode(',', $s);"),
        ("LL008", "<? echo 1; ?>", "<?php echo 1; ?>"),
        ("LL009", "eval($_GET['code']);", "echo 'safe';"),
        ("LL011", '$db_password = "hunter2";', "$db_password = getenv('DB_PASSWORD');"),
        (
            "LL013",
            "$_SESSION['user_id'] = $row['id'];",
            "session_regenerate_id(true);\n$_SESSION['user_id'] = $row['id'];",
        ),
        # LL015 — unserialize() on request input (PHP object injection)
        (
            "LL015",
            "$obj = unserialize($_GET['data']);",
            "$obj = json_decode($_GET['data']);",
        ),
        # LL016 — predictable rand()/mt_rand() for token generation
        (
            "LL016",
            "$csrf_token = rand(0, 999999);",
            "$csrf_token = bin2hex(random_bytes(32));",
        ),
    ],
)
def test_rule_positive_and_negative(rule_id, positive, negative):
    assert len(_hits(rule_id, positive)) >= 1, f"{rule_id} should flag: {positive!r}"
    assert len(_hits(rule_id, negative)) == 0, f"{rule_id} should NOT flag: {negative!r}"


def test_ll003_ignores_comment_lines():
    code = "// echo $_GET['name'];"
    assert _hits("LL003", code) == []


def test_ll005_form_without_csrf_flagged():
    code = '<form method="POST" action="x.php">\n<input name="a">\n</form>'
    assert len(_hits("LL005", code)) >= 1


def test_ll005_form_with_csrf_not_flagged():
    code = (
        '<form method="POST" action="x.php">\n'
        '<input type="hidden" name="csrf_token" value="<?= csrf_token() ?>">\n'
        '<input name="a">\n</form>'
    )
    assert _hits("LL005", code) == []


def test_ll010_upload_without_validation():
    code = "move_uploaded_file($_FILES['f']['tmp_name'], $dest);"
    assert len(_hits("LL010", code)) >= 1


def test_ll010_upload_with_validation_not_flagged():
    code = (
        "$ext = pathinfo($name, PATHINFO_EXTENSION);\n"
        "if (in_array($ext, $allowed)) {\n"
        "  move_uploaded_file($_FILES['f']['tmp_name'], $dest);\n"
        "}\n"
    )
    assert _hits("LL010", code) == []


def test_ll014_old_style_constructor():
    code = "class Foo {\n  function Foo() {}\n}"
    hits = _hits("LL014", code)
    assert any("constructor" in h[2] for h in hits)


def test_ll012_mixed_html_logic_needs_both_signals():
    only_sql = "\n".join(["$x = mysql_query($sql);"] * 5)
    assert _hits("LL012", only_sql) == []
    mixed = "\n".join(
        ["SELECT * FROM t;", "mysql_query($sql);", "$pdo->query($sql);"]
        + ["<div>", "<table>", "<tr>", "<td>"]
    )
    assert len(_hits("LL012", mixed)) == 1


def test_ll015_comment_not_flagged():
    code = "// $obj = unserialize($_POST['payload']);"
    assert _hits("LL015", code) == []


def test_ll015_all_superglobals_flagged():
    for sg in ("$_GET", "$_POST", "$_REQUEST", "$_COOKIE"):
        code = f"$obj = unserialize({sg}['data']);"
        hits = _hits("LL015", code)
        assert len(hits) >= 1, f"LL015 should flag unserialize on {sg}"


def test_ll015_safe_json_not_flagged():
    code = "$obj = json_decode($_POST['payload'], true);"
    assert _hits("LL015", code) == []
