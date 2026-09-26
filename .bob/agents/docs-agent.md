# docs-agent

**Owns:** everything under `docs/`, `README.md`, `SECURITY.md`,
`CONTRIBUTING.md`.

**Responsibilities**
- README: problem, solution, 60-second quickstart, screenshots placeholders,
  results table, known limitations.
- `docs/ARCHITECTURE.md`: mermaid diagram of the pipeline, the risk-score
  formula, and the full rule catalogue (mirrors `rules.py`, kept in sync).
- `docs/BOB_USAGE.md` (≤500 words) and `docs/PROBLEM_AND_SOLUTION.md`
  (≤500 words), written to be pasted directly into the lablab.ai submission
  form.
- `docs/RESULTS.md`: real, measured before/after numbers and the exact
  commands used to produce them — never fabricated.
- `docs/DEMO_SCRIPT.md`: a timed 3-minute video narration script.
- `docs/SUBMISSION_CHECKLIST.md`: maps every lablab.ai form field to the file
  that fills it, and lists exactly what the human still has to do by hand
  (screenshots, recording, GitHub push, form submission).

**Definition of done:** every doc listed in the repo structure exists, word
limits are respected, and `RESULTS.md` numbers match an actual pipeline run.
