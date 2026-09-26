# Security & Responsible Use

LegacyLift is a **static analysis and code-rewriting tool**. It never executes
the PHP code it scans, never makes network calls at runtime, and never sends
your source code anywhere.

**Only run LegacyLift against code you own or are explicitly authorised to
modify.** The tool will rewrite files (into a copy, under `out/modernized/`,
unless you pass `--in-place --i-have-a-backup`) and its purpose is to surface
real security weaknesses — do not point it at third-party code without
permission, and do not use its findings to attack systems you do not own.

## Reporting a vulnerability in LegacyLift itself
Open a private security advisory on the repository, or contact the maintainer
listed in `README.md`. Please do not open a public issue for security bugs.

## What the tool guards against in itself
- Never executes scanned PHP/JS.
- Refuses to follow symlinks that point outside the target directory.
- Caps individual file sizes it will read (default 5 MB, configurable).
- Fails safe on encoding errors instead of guessing.
