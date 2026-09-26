# security-agent

**Owns:** the security-critical rules and fixes: SQL injection (LL002),
XSS (LL003), weak password hashing (LL004), CSRF (LL005), dangerous
functions / LFI-RFI (LL009), hard-coded credentials (LL011), session
hardening (LL013).

**Responsibilities**
- Define precise, low-false-positive detection patterns for each rule above,
  coordinating with scanner-agent on the shared `Finding` schema.
- Design the *safe* automated fix for each: parameterised PDO queries,
  `htmlspecialchars` escaping helper, `password_hash`/`password_verify` with
  a rehash-on-login upgrade path, CSRF token helper + form injection +
  handler verification, `.env`-based secret loading.
- Write the SQL-injection regression tests (payloads such as
  `' OR '1'='1`) that must fail against the legacy code and pass against the
  modernized code.
- Review every proposed fix for behaviour-preservation before it is marked
  AUTO-FIXABLE.

**Definition of done:** zero remaining critical security findings in
`out/modernized/`, and the SQLi regression suite proves it.
