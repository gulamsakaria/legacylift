# Migration Notes — Legacy School Portal

**Target platform:** PHP 8.2 (current shared hosting will be upgraded from
PHP 5.6 next quarter — this codebase must run cleanly on 8.2 before then).

**Constraints:**
- Keep URLs unchanged — the site is indexed in Google and linked from the
  school's Facebook page; changing routes/filenames breaks those links.
- Do not touch `/uploads` — those are live student document uploads and
  must be left exactly as they are on disk.
- Keep Bangla / UTF-8 content intact everywhere — news articles and student
  names are stored in Bangla and must round-trip through any changes
  byte-for-byte identical.
- No new paid services or external APIs — the school has no budget for
  additional subscriptions; everything must keep running on the existing
  shared hosting plan.
- Logins must keep working for existing users during the upgrade — no
  forced mass password reset.

**Known pain points (from the school's IT volunteer):**
- The site currently throws raw MySQL errors to visitors sometimes.
- We suspect the login form is not very secure — a local student found they
  could see other people's data by editing the URL once.
- File uploads on the "documents" page accept anything, which makes us
  nervous.
