# Vendored copy of `legacylift`

This is a copy of `src/legacylift/` (minus `cli.py` and `webapp.py`, which
aren't needed here), plus a local copy of the root `legacylift.yaml`.

## Why a copy, not the real package

`website/` is deployed to Vercel with **Root Directory = website** (see
`website/README.md`), so the Vercel build only ever sees files inside
`website/`. It can't reach the sibling `../src/legacylift/` package one
level up in the real repo — so `website/api/scan.py` needs its own
self-contained copy of the engine to import.

## Keeping it in sync

If you change scanning/fixing/reporting logic in the real package
(`src/legacylift/`), re-copy the changed files here too — this directory
is not auto-generated. From the repo root:

```bash
rsync -a --exclude cli.py --exclude webapp.py --exclude __pycache__ \
  src/legacylift/ website/api/_vendor/legacylift/
cp legacylift.yaml website/api/_vendor/legacylift/legacylift.yaml
```

(`website/api/_vendor/legacylift/config.py` intentionally looks for
`legacylift.yaml` next to itself, not three parents up like the real
package does — see the note at the top of that file.)
