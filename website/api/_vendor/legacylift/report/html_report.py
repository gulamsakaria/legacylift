from __future__ import annotations

import json

from jinja2 import Template

from ..fixer.engine import FixResult
from ..planner import PlanItem
from ..scanner.engine import ScanResult
from ..verifier import VerifyResult

_TEMPLATE = Template(
    r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LegacyLift Report — {{ scan.root }}</title>
<style>
  :root {
    --bg: #f7f7f9; --panel: #ffffff; --text: #1b1e23; --muted: #5b6270;
    --border: #e3e5e9; --accent: #2f6fed;
    --critical: #d1273d; --high: #e2711d; --medium: #c9a227; --low: #4a90a4;
    --good: #1f9d55;
  }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#12141a; --panel:#1a1d24; --text:#e7e9ee; --muted:#9aa2b1; --border:#2a2e38; --accent:#6f9bff; }
  }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--text);
         font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif; }
  header { padding:28px 32px; border-bottom:1px solid var(--border); }
  header h1 { margin:0 0 4px; font-size:22px; }
  header .sub { color:var(--muted); font-size:14px; }
  main { max-width:1100px; margin:0 auto; padding:24px 20px 60px; }
  .cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:14px; margin:20px 0 28px; }
  @media (max-width:700px) {
    .cards { grid-template-columns: repeat(2, 1fr); }
  }
  .card { background:var(--panel); border:1px solid var(--border); border-radius:10px; padding:16px; }
  .card .n { font-size:28px; font-weight:700; }
  .card .l { color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.04em; }
  /* risk gauge */
  .gauge-wrap { display:flex; align-items:center; gap:10px; }
  .gauge-scores { display:flex; align-items:center; gap:6px; font-size:22px; font-weight:700; }
  .before-after { display:flex; align-items:center; gap:10px; font-size:22px; font-weight:700; }
  .before-after .arrow { color:var(--muted); font-size:16px; }
  .risk-before { color:var(--critical); }
  .risk-after { color:var(--good); }
  section { background:var(--panel); border:1px solid var(--border); border-radius:10px;
            padding:18px 20px; margin-bottom:20px; }
  section h2 { margin-top:0; font-size:16px; }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  th, td { text-align:left; padding:7px 8px; border-bottom:1px solid var(--border); vertical-align:top; }
  th { color:var(--muted); font-weight:600; font-size:11px; text-transform:uppercase; }
  code, .mono { font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:12px; }
  .badge { display:inline-block; padding:2px 8px; border-radius:999px; font-size:11px; font-weight:600; color:#fff; }
  .sev-critical { background:var(--critical); } .sev-high { background:var(--high); }
  .sev-medium { background:var(--medium); color:#3a2f00; } .sev-low { background:var(--low); }
  .cls-AUTO-FIXABLE { color:var(--good); font-weight:600; }
  .cls-ASSISTED { color:var(--high); font-weight:600; }
  .cls-MANUAL { color:var(--muted); font-weight:600; }
  .filters { display:flex; gap:8px; flex-wrap:wrap; margin-bottom:12px; }
  .filters select, .filters input { padding:6px 8px; border-radius:6px; border:1px solid var(--border);
                                     background:var(--bg); color:var(--text); font-size:13px; }
  .diff { white-space:pre-wrap; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
          font-size:12px; background:var(--bg); border:1px solid var(--border); border-radius:8px;
          padding:10px; max-height:260px; overflow:auto; }
  .diff .add { color:var(--good); } .diff .del { color:var(--critical); }
  details summary { cursor:pointer; font-weight:600; padding:6px 0; }
  .pass { color:var(--good); font-weight:700; } .fail { color:var(--critical); font-weight:700; }
  footer { text-align:center; color:var(--muted); font-size:12px; padding:20px; }
</style>
</head>
{#-
  risk_gauge(score) — inline SVG circular progress ring.
  r=28 → circumference C = 2π×28 ≈ 175.93
  stroke-dashoffset = C × (1 - score/100)
  Colour thresholds: ≥60 red (#d1273d), 30–59 amber (#c9a227), <30 green (#1f9d55)
  The track circle uses currentColor at low opacity so it inherits dark-mode text colour.
-#}
{% macro risk_gauge(score) -%}
{%- set score = [score|int, 0]|max %}
{%- set score = [score, 100]|min %}
{%- set circ = 175.93 %}
{%- set offset = circ * (1 - score / 100) %}
{%- if score >= 60 %}
  {%- set colour = "#d1273d" %}
{%- elif score >= 30 %}
  {%- set colour = "#c9a227" %}
{%- else %}
  {%- set colour = "#1f9d55" %}
{%- endif %}
<svg width="64" height="64" viewBox="0 0 64 64" aria-label="Risk score {{ score }}/100" role="img"
     style="flex:none;display:block;">
  <circle cx="32" cy="32" r="28" fill="none" stroke="currentColor" stroke-opacity="0.12" stroke-width="6"/>
  <circle cx="32" cy="32" r="28" fill="none" stroke="{{ colour }}" stroke-width="6"
          stroke-linecap="round" stroke-dasharray="{{ circ }}"
          stroke-dashoffset="{{ "%.2f"|format(offset) }}"
          transform="rotate(-90 32 32)"/>
  <text x="32" y="37" text-anchor="middle" font-size="13" font-weight="700"
        font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif"
        fill="{{ colour }}">{{ score }}</text>
</svg>
{%- endmacro %}
<body>
<header>
  <h1>LegacyLift Report</h1>
  <div class="sub">{{ scan.root }} · {{ scan.files_scanned }} files scanned · generated by LegacyLift v0.1.0</div>
</header>
<main>

  <div class="cards">
    <div class="card">
      <div class="gauge-wrap">
        {% if verify %}
          {{ risk_gauge(verify.before_risk_score) }}
          {% if verify.after_risk_score != verify.before_risk_score %}
          <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true" style="flex:none;color:var(--muted)">
            <path d="M3 7h8M7.5 3.5l3.5 3.5-3.5 3.5" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          {{ risk_gauge(verify.after_risk_score) }}
          {% endif %}
        {% else %}
          {{ risk_gauge(scan.project_risk_score) }}
        {% endif %}
        <div class="gauge-scores">
          {% if verify %}
            <span class="risk-before">{{ verify.before_risk_score }}</span>
            <span style="color:var(--muted);font-size:16px">→</span>
            <span class="risk-after">{{ verify.after_risk_score }}</span>
          {% else %}
            {{ scan.project_risk_score }}
          {% endif %}
        </div>
      </div>
      <div class="l" style="margin-top:8px">Risk score (0–100)</div>
    </div>
    <div class="card"><div class="n">{{ scan.findings_by_severity.get('critical', 0) }}</div><div class="l">Critical findings</div></div>
    <div class="card"><div class="n">{{ scan.findings|length }}</div><div class="l">Total findings</div></div>
    <div class="card"><div class="n">{{ scan.estimated_manual_hours|round(1) }}h</div><div class="l">Manual effort (est.)</div></div>
    <div class="card"><div class="n">{{ scan.estimated_legacylift_hours|round(1) }}h</div><div class="l">LegacyLift review effort (est.)</div></div>
  </div>

  {% if verify %}
  <section>
    <h2>Verification: <span class="{{ 'pass' if verify.passed else 'fail' }}">{{ 'PASSED' if verify.passed else 'FAILED' }}</span></h2>
    <table>
      <tr><th></th><th>Before</th><th>After</th></tr>
      <tr><td>Risk score</td><td>{{ verify.before_risk_score }}</td><td>{{ verify.after_risk_score }}</td></tr>
      <tr><td>Total findings</td><td>{{ verify.before_findings }}</td><td>{{ verify.after_findings }}</td></tr>
      <tr><td>Critical findings</td><td>{{ verify.before_by_severity.get('critical', 0) }}</td><td>{{ verify.after_by_severity.get('critical', 0) }}</td></tr>
    </table>
    {% if verify.lint.available %}
    <p><code>php -l</code>: {{ verify.lint.checked }} file(s) checked, {{ verify.lint.failed|length }} failed.</p>
    {% else %}
    <p><em>{{ verify.lint.skipped_reason }}</em></p>
    {% endif %}
  </section>
  {% endif %}

  {% if fix %}
  <section>
    <h2>Fixes applied</h2>
    <table>
      <tr><th>Rule</th><th>Changes applied</th></tr>
      {% for rid, count in fix.applied_by_rule.items()|sort %}
      <tr><td class="mono">{{ rid }}</td><td>{{ count }}</td></tr>
      {% endfor %}
    </table>
    {% if fix.assisted_by_rule %}
    <h2 style="margin-top:18px;">Flagged for manual review (ASSISTED)</h2>
    <table>
      <tr><th>Rule</th><th>Items</th></tr>
      {% for rid, count in fix.assisted_by_rule.items()|sort %}
      <tr><td class="mono">{{ rid }}</td><td>{{ count }}</td></tr>
      {% endfor %}
    </table>
    {% endif %}
  </section>
  {% endif %}

  <section>
    <h2>Migration plan</h2>
    <table>
      <tr><th>#</th><th>Rule</th><th>Title</th><th>Severity</th><th>Classification</th><th>Findings</th></tr>
      {% for p in plan %}
      <tr>
        <td>{{ loop.index }}</td>
        <td class="mono">{{ p.rule_id }}</td>
        <td>{{ p.title }}</td>
        <td><span class="badge sev-{{ p.severity }}">{{ p.severity }}</span></td>
        <td class="cls-{{ p.classification }}">{{ p.classification }}</td>
        <td>{{ p.finding_count }}</td>
      </tr>
      {% endfor %}
    </table>
  </section>

  <section>
    <h2>Findings</h2>
    <div class="filters">
      <select id="fRule"><option value="">All rules</option>{% for r in rule_ids %}<option>{{ r }}</option>{% endfor %}</select>
      <select id="fSev"><option value="">All severities</option><option>critical</option><option>high</option><option>medium</option><option>low</option></select>
      <input id="fFile" type="text" placeholder="filter by filename…">
    </div>
    <table id="findingsTable">
      <thead><tr><th>Severity</th><th>Rule</th><th>File</th><th>Line</th><th>Explanation</th></tr></thead>
      <tbody>
      {% for f in findings %}
      <tr data-rule="{{ f.rule_id }}" data-sev="{{ f.severity }}" data-file="{{ f.file|lower }}">
        <td><span class="badge sev-{{ f.severity }}">{{ f.severity }}</span></td>
        <td class="mono">{{ f.rule_id }}</td>
        <td class="mono">{{ f.file }}</td>
        <td>{{ f.line }}</td>
        <td>{{ f.explanation }}</td>
      </tr>
      {% endfor %}
      </tbody>
    </table>
  </section>

  {% if diffs %}
  <section>
    <h2>Diffs ({{ diffs|length }} file(s) changed)</h2>
    {% for d in diffs %}
    <details>
      <summary class="mono">{{ d.path }} ({{ d.applied|length }} fix note(s))</summary>
      <ul>
        {% for note in d.applied %}<li>{{ note }}</li>{% endfor %}
      </ul>
      <div class="diff">{{ d.diff_html|safe }}</div>
    </details>
    {% endfor %}
  </section>
  {% endif %}

</main>
<footer>LegacyLift — offline static analysis, no data leaves this machine.</footer>
<script>
  const rows = Array.from(document.querySelectorAll('#findingsTable tbody tr'));
  function applyFilters() {
    const rule = document.getElementById('fRule').value;
    const sev = document.getElementById('fSev').value;
    const file = document.getElementById('fFile').value.toLowerCase();
    rows.forEach(r => {
      const show = (!rule || r.dataset.rule === rule)
                && (!sev || r.dataset.sev === sev)
                && (!file || r.dataset.file.includes(file));
      r.style.display = show ? '' : 'none';
    });
  }
  document.getElementById('fRule').addEventListener('change', applyFilters);
  document.getElementById('fSev').addEventListener('change', applyFilters);
  document.getElementById('fFile').addEventListener('input', applyFilters);
</script>
</body>
</html>
"""
)


def _escape_diff_line(line: str) -> str:
    return (
        line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )


def _diff_to_html(diff_text: str) -> str:
    out = []
    for line in diff_text.splitlines():
        esc = _escape_diff_line(line)
        if line.startswith("+") and not line.startswith("+++"):
            out.append(f'<span class="add">{esc}</span>')
        elif line.startswith("-") and not line.startswith("---"):
            out.append(f'<span class="del">{esc}</span>')
        else:
            out.append(esc)
    return "\n".join(out)


def render_html_report(
    scan: ScanResult,
    plan: list[PlanItem],
    fix_result: FixResult | None,
    verify_result: VerifyResult | None,
) -> str:
    findings_sorted = sorted(
        scan.findings, key=lambda f: ({"critical": 0, "high": 1, "medium": 2, "low": 3}.get(f.severity, 9), f.rule_id)
    )
    rule_ids = sorted({f.rule_id for f in scan.findings})

    diffs = []
    if fix_result is not None:
        for fo in fix_result.files:
            if fo.changed:
                diffs.append(
                    {"path": fo.path, "applied": fo.applied, "diff_html": _diff_to_html(fo.diff)}
                )

    return _TEMPLATE.render(
        scan=scan,
        findings=findings_sorted,
        rule_ids=rule_ids,
        plan=plan,
        fix=fix_result.to_dict() if fix_result else None,
        verify=verify_result.to_dict() if verify_result else None,
        diffs=diffs,
        json=json,
    )
