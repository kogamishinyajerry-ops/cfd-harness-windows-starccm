# Audit signing & verification

Every V&V run emits a signed `audit.json` (HMAC-SHA-256 over a canonical,
byte-deterministic manifest). This doc is the operator guide; the trust
model and its rationale are in
[`reports/decisions/DEC-010-audit-signing-key-trust.md`](../reports/decisions/DEC-010-audit-signing-key-trust.md).

## 1. Provision a signing key (once)

```bash
python -c "import secrets; print(secrets.token_hex(32))"   # 256-bit key
export CFD_HARNESS_SIGN_KEY=<that value>          # CI: inject from secrets manager
```

There is **no** production key in the source. Without `CFD_HARNESS_SIGN_KEY`
(or `--sign-key`), runs sign with an explicitly **untrusted** dev key and the
audit is stamped `key_source=dev-unsigned`, `trusted=false`. That is fine for
mock/CI smoke (which can never be `validated` anyway) — it is just honest.

## 2. Produce an audit

```bash
python -m cfd_harness.cli.run --case lid_driven_cavity --executor mock
# -> reports/audit/<case>/<ts>/audit.json   (manifest + signature + signing block)
```

## 3. Verify an audit

```bash
# Integrity + trust policy (rejects dev-unsigned, checks HMAC under your key):
CFD_HARNESS_SIGN_KEY=<key> python -m cfd_harness.audit_package.verify path/to/audit.json

# Pin the exact production key (recommended in CI gates):
python -m cfd_harness.audit_package.verify audit.json --key <key> --expect-key-id <id>

# Dev: check integrity only, tolerate an untrusted source:
python -m cfd_harness.audit_package.verify audit.json --key <key> --allow-untrusted
```

Exit code: `0` accepted, `1` rejected (reasons printed), `2` usage/IO error.

Or programmatically:

```python
from cfd_harness.audit_package.verify import verify_audit_file
res = verify_audit_file("audit.json", key, expected_key_id="<prod-fingerprint>")
assert res.accepted, res.reasons
```

## Verifier policy (what "accepted" means)

An audit is **accepted** only when ALL hold:
1. the HMAC verifies under your key (integrity + authenticity), **and**
2. `key_id` is not the dev-unsigned fingerprint and `key_source == "provided"`
   (unless `--allow-untrusted`), **and**
3. if you pin `--expect-key-id`, the audit's `key_id` matches it.

`trusted` in the audit's `signing` block is advisory; the authoritative
checks are the HMAC + the `key_id`. A `validated` verdict (`is_validated:true`)
should only ever be cited from an **accepted, trusted** audit.

## Quality gate

`scripts/quality_gate.py` enforces all of the above in one command (suitable
for CI / pre-release):

```bash
python scripts/quality_gate.py            # mock suite + coverage>=85% + trust invariants
python scripts/quality_gate.py --fast     # trust invariants only (no pytest run)
```

It runs the mock test suite with a coverage floor and re-asserts the
load-bearing invariants — the MOCK WARN ceiling, dev-unsigned rejection +
integrity-only acceptance, and tamper detection — exiting non-zero if any
guarantee regresses.
