from pathlib import Path

from legacylift.config import load_default_config
from legacylift.scanner.engine import scan_path
from legacylift.tests_gen import generate_tests


def test_generate_tests_for_sqli_and_weak_hash(tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    (project / "login.php").write_text(
        "<?php\n"
        "$sql = \"SELECT * FROM users WHERE username = '\" . $_POST['username'] . \"'\";\n"
        "$r = mysql_query($sql);\n"
        "$row = mysql_fetch_assoc($r);\n"
        "if ($row['password'] == md5($_POST['password'])) { ok(); }\n"
        "echo $_GET['x'];\n",
        encoding="utf-8",
    )
    cfg = load_default_config()
    scan = scan_path(project, cfg)
    out_dir = tmp_path / "generated"
    written = generate_tests(scan, project, out_dir)
    assert any("sqli" in w for w in written)
    assert any("login" in w for w in written)
    for w in written:
        assert (out_dir / w).exists()
        content = (out_dir / w).read_text(encoding="utf-8")
        assert "PHPUnit" in content or "TestCase" in content


def test_generate_tests_empty_project_writes_nothing(tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    (project / "clean.php").write_text("<?php\necho 'hi';\n", encoding="utf-8")
    cfg = load_default_config()
    scan = scan_path(project, cfg)
    written = generate_tests(scan, project, tmp_path / "generated")
    assert written == []
