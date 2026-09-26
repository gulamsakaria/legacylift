from pathlib import Path

from legacylift.config import load_default_config
from legacylift.fixer.engine import run_fixer
from legacylift.planner import build_plan
from legacylift.report import write_all_reports
from legacylift.scanner.engine import scan_path
from legacylift.verifier import verify


def test_full_report_pipeline_runs_and_writes_files(tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    (project / "a.php").write_text(
        "<?php\n$r = mysql_query($sql);\necho $_GET['x'];\n", encoding="utf-8"
    )
    cfg = load_default_config()
    scan = scan_path(project, cfg)
    plan = build_plan(scan)
    out_dir = tmp_path / "out"
    fix_result = run_fixer(project, cfg, out_dir, apply=True)
    vr = verify(scan, fix_result.modernized_root, cfg)
    paths = write_all_reports(scan, plan, fix_result, vr, out_dir)
    assert paths["html"].exists()
    assert paths["json"].exists()
    assert paths["md"].exists()
    html = paths["html"].read_text(encoding="utf-8")
    assert "<html" in html.lower()
    assert "Risk score" in html
    # Gauge: at least one SVG ring element must be present
    assert "<svg" in html
    assert "stroke-dashoffset" in html
