"""End-to-end CLI tests via legacylift.cli.main(), exercising every
subcommand against a small throwaway project."""

from pathlib import Path

import pytest

from legacylift.cli import main


@pytest.fixture()
def vuln_project(tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    (project / "login.php").write_text(
        "<?php\n"
        "$conn = mysql_connect('h', 'u', 'p');\n"
        "mysql_select_db('db');\n"
        "if ($_SERVER['REQUEST_METHOD'] == 'POST') {\n"
        "  $sql = \"SELECT * FROM users WHERE username = '\" . $_POST['username'] . \"'\";\n"
        "  $r = mysql_query($sql);\n"
        "  $row = mysql_fetch_assoc($r);\n"
        "  if ($row && $row['password'] == md5($_POST['password'])) {\n"
        "    $_SESSION['user_id'] = $row['id'];\n"
        "    echo $_GET['name'];\n"
        "  }\n"
        "}\n"
        "?>\n"
        '<form method="POST" action="login.php"><input name="username"></form>\n',
        encoding="utf-8",
    )
    return project


def test_cli_scan(vuln_project, tmp_path, capsys):
    rc = main(["scan", str(vuln_project), "--out", str(tmp_path / "out")])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Risk score" in out
    assert (tmp_path / "out" / "scan.json").exists()


def test_cli_plan(vuln_project, tmp_path):
    rc = main(["plan", str(vuln_project), "--out", str(tmp_path / "out")])
    assert rc == 0
    assert (tmp_path / "out" / "plan.md").exists()
    assert (tmp_path / "out" / "plan.json").exists()


def test_cli_fix_apply(vuln_project, tmp_path):
    rc = main(["fix", str(vuln_project), "--apply", "--out", str(tmp_path / "out")])
    assert rc == 0
    modernized = tmp_path / "out" / "modernized" / "login.php"
    assert modernized.exists()
    content = modernized.read_text(encoding="utf-8")
    assert "mysql_query" not in content


def test_cli_fix_in_place_requires_confirmation(vuln_project, tmp_path):
    rc = main(["fix", str(vuln_project), "--in-place", "--out", str(tmp_path / "out")])
    assert rc == 1


def test_cli_tests(vuln_project, tmp_path):
    rc = main(["tests", str(vuln_project), "--out", str(tmp_path / "gen")])
    assert rc == 0
    assert any((tmp_path / "gen").iterdir())


def test_cli_verify(vuln_project, tmp_path):
    main(["fix", str(vuln_project), "--apply", "--out", str(tmp_path / "out")])
    rc = main(["verify", str(vuln_project), "--modernized", str(tmp_path / "out" / "modernized")])
    assert rc == 0


def test_cli_run_full_pipeline(vuln_project, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rc = main(["run", str(vuln_project), "--out", str(tmp_path / "out")])
    assert rc == 0
    assert (tmp_path / "out" / "report.html").exists()
    assert (tmp_path / "tests" / "generated").exists()


def test_cli_ingest(vuln_project, tmp_path):
    doc = tmp_path / "MIGRATION_NOTES.md"
    doc.write_text("Target PHP 8.2. Do not touch `/uploads`. Keep Bangla/UTF-8 content.", encoding="utf-8")
    rc = main(["ingest", str(doc), str(vuln_project)])
    assert rc == 0
    assert (vuln_project / "legacylift.yaml").exists()


def test_cli_version(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])
    assert exc_info.value.code == 0
