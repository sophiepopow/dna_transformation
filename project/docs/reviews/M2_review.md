# M2 Review — Classical Encryption Layer & Pipeline Composition

Date: 2026-08-16
Reviewer: independent review subagent (milestone-reviewer methodology),
first cycle — no retries needed.

## Verdict: PASS

## Exit criteria checklist

| Criterion | Command | Result |
|---|---|---|
| `pytest tests/test_pipeline.py -v` 100% pass | `/Users/sophiepopow/Documents/PK/master/dna/.venv/bin/python -m pytest tests/test_pipeline.py -v` (from `project/`) | **4 passed** in 4.90s |
| Both pipelines byte-identical round-trip on all 20 test vectors | Same run (20 seeded random byte strings, 10 B–200 KB, per pipeline) + manual invocation on `b""`, `b"a"`, a 500-byte random sample, and a 495-byte repeated-text sample | All round-tripped exactly, including the empty-bytes edge case |
| Pipeline A dict has 3 stage keys, Pipeline B has 2 | `test_stage_keys_present` (pass) + direct manual invocation | `Pipeline A: ['input', 'post_dna', 'post_classical']`; `Pipeline B: ['input', 'post_classical']` |

Full suite independently re-run: `pytest tests/ -v` → **14 passed** in 6.32s
(M1's 10 tests + M2's 4, all green).

## Design concerns (surfaced despite PASS)

- **Nonce freshness — explicitly checked, confirmed correct.** `encrypt_aes_gcm`
  calls `AES.new(key, AES.MODE_GCM)` with no explicit nonce, so pycryptodome
  auto-generates a fresh random nonce per call. Reviewer encrypted identical
  plaintext 200 times under the fixed experiment key and got 200 unique
  nonces/ciphertexts. This mattered to check explicitly (not just trust)
  because a deterministic/reused nonce under a fixed GCM key would be a
  real cryptographic break, and would still have passed every round-trip
  test in the suite — the same class of "tests pass, design is unsound"
  failure this project has been burned by before (see M1 history).
- **AES-GCM tamper/auth-failure behavior is untested by the committed
  suite.** Reviewer manually confirmed `decrypt_aes_gcm` correctly raises on
  a wrong key, a corrupted ciphertext byte, and a corrupted tag byte (all
  three: `ValueError: MAC check failed`). Behavior is sound, but this is
  currently verified only by the reviewer's ad hoc script, not by a
  committed test. **Recommended, non-blocking:** add
  `tests/test_classical_crypto.py` (or extend `test_pipeline.py`) with
  explicit tamper-detection assertions before this layer is relied on
  further (M4 avalanche testing, M6 experiment).
- **`reference_sequence` is genuinely wired to `data/reference_sequence.txt`**,
  not a hardcoded literal duplicated elsewhere — confirmed `post_dna !=
  input` for non-empty samples (the DNA stage does real work) and found no
  competing hardcoded reference string in `src/` or `tests/`.
- **`data/aes_key.bin` reuse confirmed independently** (mtime + MD5
  unchanged across a full test run), not just trusted from the
  implementer's own claim.
- **`mask` → `reference_sequence` rename is consistent everywhere** — no
  leftover `mask: bytes` signatures; remaining `mask`/`derive_mask` text is
  historical prose about the superseded M1 design.
- **The decrypt function signatures deviate from the plan's literal
  one-argument pseudocode** (`decrypt_pipeline_a(stages, key,
  reference_sequence)`, `decrypt_pipeline_b(stages, key)`, nonce/tag carried
  inside the `post_classical` stage dict). Judged justified and
  self-consistent: the plan's one-arg pseudocode cannot actually work (AES-GCM
  decryption needs the key; Pipeline A's inverse needs the reference
  sequence too), and the actual implementation was confirmed genuinely
  invertible by direct invocation, not just plausible-sounding. Documented
  transparently in `src/pipeline.py`'s module docstring.
- **Scope note, not a defect:** M2 doesn't touch whether the DNA-transform's
  entropy-preserving property survives AES-GCM — that's M4/M6 territory.
  `post_dna` is exposed as its own untouched stage key, so nothing here
  interferes with that later measurement.

## Required fixes

None. No retry cycle was needed.
