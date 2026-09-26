# LegacyLift website

A static landing page (`index.html` + `styles.css` + `script.js`, no
build step) **plus one real Python serverless function**
(`api/scan.py`) that runs the actual LegacyLift pipeline against
whatever a visitor uploads — this isn't a mockup, `#scan` on the live
site does a real scan.

- `sample-report/report.html` — a real copy of a generated LegacyLift
  report (see `docs/sample-report/` in the repo root), embedded live in
  the "Sample report" section.
- `api/scan.py` — a Flask app exporting `app`; Vercel auto-detects this
  and serves it at `POST /api/scan`. It vendors a copy of the scan
  engine at `api/_vendor/legacylift/` — see `api/_vendor/README.md` for
  why, and how to keep it in sync if you change the real engine in
  `src/legacylift/`.

## Deploy to Vercel

1. Push the repo to GitHub (see the root `docs/SUBMISSION_CHECKLIST.md`).
2. On [vercel.com](https://vercel.com) → **Add New… → Project** → import
   that GitHub repo.
3. When asked for the **Root Directory**, set it to `website`.
4. Framework preset: **Other**. Build command: none. Output directory:
   `./` (leave default). Click **Deploy** — Vercel installs
   `api/requirements.txt` automatically and wires `api/scan.py` up as a
   serverless function; everything else is served as static files.

Every push to the connected branch redeploys automatically.

### Known limits of the live `/api/scan` (by design, not bugs)

- **~4 MB upload cap** — Vercel Serverless Functions cap the request
  body around there on most plans; `api/scan.py` enforces the same
  limit itself so the error is a clean message, not a platform 413.
- **No run history** — each request runs in its own temp directory that
  is deleted before the response is sent. Unlike the local dashboard
  (`legacylift dashboard`), there's no shared filesystem between
  invocations to persist a list of past runs.
- **Single-request timeout** — the whole pipeline must finish inside
  Vercel's function execution limit (10s on Hobby by default). Fine for
  a single file or a small demo zip; a large real-world codebase should
  use the CLI or the local dashboard instead, which is what the
  "Want the full local dashboard?" section points people to.

## Run it locally

The static site alone:

```bash
cd website
python -m http.server 5500
# open http://localhost:5500 — note /api/scan won't work this way
```

To test the upload form too (mimics Vercel's routing — static files at
`/`, the Flask function at `/api/scan` — using one local Flask process):

```bash
cd website
pip install -r api/requirements.txt
python dev_server.py        # http://127.0.0.1:5500
```
