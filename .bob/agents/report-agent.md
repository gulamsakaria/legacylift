# report-agent

**Owns:** `src/legacylift/report/` — HTML, JSON, and Markdown output.

**Responsibilities**
- Build one self-contained `out/report.html` (inline CSS/JS, no CDN,
  prefers-color-scheme aware) showing: project risk score before/after,
  findings table (filterable by rule/severity/file), per-file risk, the
  manual-vs-LegacyLift effort comparison, and side-by-side diffs for every
  applied fix.
- Mirror the same data as `out/report.json` (machine-readable) and
  `out/report.md` (for pasting into PRs/issues).
- Keep the report deterministic: stable ordering, no embedded timestamps in
  diffs (a single "generated at" field is fine at the top).

**Definition of done:** `out/report.html` opens correctly with no external
requests, correctly reflects real scan/fix data, and a copy is saved to
`docs/sample-report/`.
