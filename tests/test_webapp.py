"""Tests for the Flask upload dashboard (webapp.py) -- requires the
'serve' extra (Flask). Skipped entirely if Flask isn't installed."""

import io
import zipfile

import pytest

flask = pytest.importorskip("flask")

from legacylift.webapp import create_app  # noqa: E402


@pytest.fixture()
def client(tmp_path):
    app = create_app(tmp_path / "dashboard_data")
    app.config["TESTING"] = True
    return app.test_client()


def _make_zip(files: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def test_index_page_loads(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"LegacyLift" in resp.data


def test_upload_single_php_file_runs_pipeline(client):
    php_code = b"<?php\n$r = mysql_query($sql);\necho $_GET['x'];\n"
    data = {"project": (io.BytesIO(php_code), "vuln.php")}
    resp = client.post("/upload", data=data, content_type="multipart/form-data")
    # Redirects to the generated report on success.
    assert resp.status_code == 302
    assert "/report.html" in resp.headers["Location"]


def test_upload_rejects_unsupported_extension(client):
    data = {"project": (io.BytesIO(b"not php"), "notes.txt")}
    resp = client.post("/upload", data=data, content_type="multipart/form-data")
    assert resp.status_code == 400
    assert b"Unsupported file type" in resp.data


def test_upload_zip_with_project_folder(client):
    zip_bytes = _make_zip({"myproj/index.php": "<?php\nmysql_query($sql);\n"})
    data = {"project": (io.BytesIO(zip_bytes), "myproj.zip")}
    resp = client.post("/upload", data=data, content_type="multipart/form-data")
    assert resp.status_code == 302


def test_upload_rejects_zip_slip_path_traversal(client):
    # A malicious zip entry that tries to escape the extraction directory.
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../../evil.php", "<?php echo 'pwned'; ?>")
    data = {"project": (io.BytesIO(buf.getvalue()), "evil.zip")}
    resp = client.post("/upload", data=data, content_type="multipart/form-data")
    assert resp.status_code == 400
    assert b"Unsafe path" in resp.data


def test_upload_empty_project_with_no_php_files(client):
    zip_bytes = _make_zip({"readme.txt": "hello"})
    data = {"project": (io.BytesIO(zip_bytes), "empty.zip")}
    resp = client.post("/upload", data=data, content_type="multipart/form-data")
    assert resp.status_code == 400
    assert b"No .php files found" in resp.data


def test_report_file_route_blocks_path_traversal(client):
    resp = client.get("/runs/somerun/../../../etc/passwd")
    assert resp.status_code == 404
