# DEC-010 — Audit signing-key trust model hardening

- **Status:** accepted (remediated) — 2026-06-13
- **Trigger:** security audit of the HMAC signing path (user-requested).
- **Related:** ground rule #4 "byte-deterministic signed audit package";
  the MOCK/real verdict ceiling (DEC-005); `is_validated` semantics.

## Context

The audit package's entire value proposition is a **tamper-evident,
citable, signed manifest** (`audit.json` = Manifest + HMAC-SHA-256
signature). An HMAC is only trustworthy if the **key is secret**. A
security audit (a runnable forgery PoC + an independent security-reviewer
pass) found the key was effectively public and the trust model had several
holes.

## Findings (audited 2026-06-13)

| ID | Sev | File | Issue |
|---|---|---|---|
| C-1 | CRITICAL | `cli/run.py:157` | **Hardcoded default key** `"cfd-harness-dev-key"` (in source + git history); no env/keyfile source. **Forgery PoC confirmed**: anyone can mint `is_validated=True, is_mock=False, verdict_level=PASS` and it verifies. |
| C-2 | CRITICAL | `sign.py`/`manifest.py` | **No key-identity binding** — a verifier can't tell which key signed an audit, nor distinguish a dev-signed from a prod-signed one. |
| C-3 | CRITICAL | `sign.py` | **`signed_at` was outside the signed payload** → timestamps backdatable without breaking the signature. |
| H-1 | HIGH | `sign.py:42` | No minimum key length (only rejected empty). |
| H-2 | HIGH | `cli/run.py` | `verify_recipe` was **non-runnable** and always returned False (`Signature(digest="")`), misleading verifiers. |
| H-3 | HIGH | `serialize.py` | `nan`/`inf` would emit non-RFC-8259 `NaN`/`Infinity` → cross-verifier non-determinism / false tamper. |
| M-1 | MED | `serialize.py` | No Unicode NFC normalization → NFC-vs-NFD strings sign differently (false tamper across platforms). |
| M-2 | MED | `cli/run.py:254` | `case_id` flows into `audit_dir` path unsanitized (programmatic `TaskSpec` callers could traverse). |
| M-3 | MED | `sign.py` | Unauthenticated `digest` field invites "verify the digest" confusion (verify() does require both, so not a bypass). |

## Decision (remediation — landed in this pass)

1. **No production key in source.** Key sourced from `--sign-key`
   > `CFD_HARNESS_SIGN_KEY` env. If neither is set, the CLI falls back to
   an **explicitly untrusted, labelled** dev key and stamps the audit
   `key_source="dev-unsigned"`, `trusted=false`, with a loud stderr
   warning. (The dev key exists only so mock/CI runs — which can never be
   `validated` — still emit an audit file; it is **not** a secret.)
2. **Key-identity binding (`key_id`).** `Signature.key_id` =
   `sha256("cfd-harness-keyid:v1:" + key)[:16]` — a non-secret,
   non-reversible fingerprint. `verify()` requires the recomputed
   fingerprint of the supplied key to match, so: a signature made with key
   A never verifies under key B, and a verifier can **blocklist the
   dev-unsigned `key_id`**. Forgery is now *attributable* and a forged
   "validated" audit **does not verify under the real production key**.
3. **Authenticated timestamp.** `signed_at` is bound into the HMAC payload
   (a `\x1f` separator + the ISO timestamp is appended before hashing), so
   it cannot be backdated without breaking the signature.
4. **Minimum 32-byte (256-bit) keys** enforced in `Signer`; the CLI
   returns exit 2 on a short key.
5. **Deterministic serialization:** `allow_nan=False` + recursive **NFC**
   normalization in `serialize_manifest`.
6. **`audit.json` trust block** (`signing.{key_source,trusted,min_key_bytes}`)
   + `signature.key_id` + a **corrected, runnable** `verify_recipe`;
   `case_id` is path-sanitized at `audit_dir`.
7. **`SCHEMA_VERSION` 1 → 2** — old v1 signatures no longer verify
   (intended; they were all dev-key / untrusted anyway).

## Verifier policy (REQUIRED of any consumer)

A production verifier MUST: (a) read `signature.key_id`, (b) confirm it
equals the **expected production key fingerprint** (reject the dev
`key_id` / `key_source != "provided"`), and (c) run
`Signature(**sig).verify(Manifest(**manifest), prod_key)`. `trusted` in
the audit is advisory; `key_id` + a held secret are authoritative.

## Residual risk / follow-ups (deferred)

- **Key provisioning is operational**: generate with
  `python -c "import secrets; print(secrets.token_hex(32))"`, store in CI
  secrets / a secrets manager, set `CFD_HARNESS_SIGN_KEY`. Until a real
  key is provisioned, every audit is `dev-unsigned` (and honestly says so).
- **No key rotation / expiry / revocation yet** (L-1) — add a signed
  `key_id -> (not_before, not_after)` map when the audit trail becomes
  load-bearing (no real run is `validated` today per DEC-005).
- **`TaskSpec` field validation** (M-2) — the `audit_dir` site is now
  guarded, but `TaskSpec.case_id` itself is still unvalidated for other
  call sites.

## Evidence
- Forgery PoC + the 8 regression tests in
  `tests/audit_package/test_sign.py` (key_id attribution, cross-key reject,
  dev-key attributable, backdating breaks verify, nan rejected, NFC equal).
- Suite: 228 passed, 0 failed (`-m "not real_solver"`).
