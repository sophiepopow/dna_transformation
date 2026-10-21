# M4 Review — Statistical Metrics Module

Date: 2026-08-23
Reviewer: independent review subagent (milestone-reviewer methodology),
first cycle — no retries needed.

## Verdict: PASS

**With an important caveat: the exit criteria as written in
`docs/milestone_plan.md` are not adequate to validate what this milestone's
avalanche test is actually supposed to demonstrate.** This is a documented,
surfaced concern, not a hidden defect — per this project's review
methodology, that does not by itself force a FAIL, but it must not be
read as "avalanche testing is done and meaningful" either. See "Central
finding" below before treating M6's reuse of this metric as informative.

## Exit criteria checklist

| Criterion | Command | Result |
|---|---|---|
| `pytest tests/test_metrics.py tests/test_avalanche.py -v` 100% pass | `/Users/sophiepopow/Documents/PK/master/dna/.venv/bin/python -m pytest tests/test_metrics.py tests/test_avalanche.py -v -s` | **17 passed** in 1.38s |
| Random-file entropy > 7.9 bits/byte | Called `shannon_entropy` directly on `os.urandom(20000)` and `data/corpus/random_small.bin` | 7.991 and 7.980 — matches `baseline_entropy.csv` to 5-6 decimals |
| Text-file entropy ~4-5 bits/byte | Called `shannon_entropy` directly on `text_small.txt`, `json_small.json` | 4.727 and 4.520 |
| Avalanche % for both pipelines in 40-60% | Full run output | Pipeline A 50.09%, Pipeline B 50.04% |

Full suite independently re-run: `pytest tests/ -v` → **37 passed** (20
pre-existing + 17 new).

Metrics functions spot-checked directly (not just via the test suite):
`shannon_entropy`, `chi_square_uniform`, `compression_ratio`,
`pearson_correlation` all behave correctly on hand-picked inputs — no
mocking, hardcoding, or hidden bugs found. `pearson_correlation` between
plaintext and its own `post_dna`/ciphertext output landed near 0 (-0.0024,
0.0032), consistent with the DNA transform destroying linear correlation
with the input as intended. `chi_square_uniform`/`pearson_correlation`
coverage, though not literally required by M4's test list, was added
proactively by the implementer — not a repeat of M2's tamper-detection gap.

## Central finding: `avalanche_test` does not measure avalanche/diffusion

Independently reproduced **three separate ways**, not just accepted from
the implementer's own report:

1. Re-ran `scripts/check_avalanche_nonce_sensitivity.py` (bit-flip vs.
   no-flip-at-all) — confirmed ~50% either way, both pipelines.
2. New variant: two entirely unrelated random inputs (not a bit-flip pair
   at all) through both pipelines — also ~50% (A: mean 49.96%, min 49.56,
   max 50.31; B: mean 50.01%, min 49.78, max 50.41) — same band, same
   variance profile as the bit-flip condition.
3. Direct read of `src/classical_crypto.py` confirms every `encrypt_aes_gcm`
   call generates a fresh random nonce, with no override available.

**Bit-flip, no-flip, and wholly-unrelated-input are statistically
indistinguishable** through the full-pipeline AES-GCM ciphertext. The test
is measuring AES-GCM's semantic-security property (any two encryptions
under fresh nonces look like independent random strings), not the
pipeline's sensitivity to the specific input change being tested. This
parallels the M1 SHA-256-mask failure mode: a test that satisfies its own
literal exit criteria for a reason unrelated to what it claims to measure.

**Reviewer's independent judgment on the design tradeoff:** endorse the
implementer's decision to keep the literal spec (natural random nonce)
over a fixed-nonce alternative — but for a sharper reason than "fixed
nonce breaks Pipeline B's 40-60% band." AES-GCM's core is CTR-mode
keystream XOR; under a *fixed* nonce, a single flipped plaintext bit
produces, by linear construction, exactly one flipped ciphertext bit.
"Avalanche effect" (block-cipher-style diffusion of one input bit across
many output bits) doesn't apply to stream-cipher-mode ciphertext the way
M4's reference paper (INRU, a block-cipher study) assumes. Neither nonce
policy makes full-pipeline AES-GCM output a meaningful avalanche
measurement — one hides the signal in nonce noise, the other correctly
proves there's no diffusion of that kind to find at the AES-GCM layer.

**Recommended direction, not implemented as part of M4 (out of this
milestone's scope):** if a genuinely meaningful avalanche number is wanted
for the thesis, measure it on the DNA-transform's own pre-AES output for
Pipeline A specifically (where a fixed-nonce-equivalent check found ~38%,
high variance — noisy, but at least reflects the chained mod-4 transform's
real diffusion, unlike the current full-pipeline number).

**Carry-forward warning for M6:** `docs/milestone_plan.md`'s M6 task list
specifies reusing `avalanche_test` with `n_trials=25` against the same
full-pipeline signature. Doing so without addressing this finding would
let the thesis present a number that actually means "AES-GCM is
semantically secure" as if it meant "the DNA transform contributes
properly to diffusion" — a mismatch between what's measured and what's
claimed. This should be decided explicitly before M6, not carried
silently into the results chapter.

## Required fixes

None — verdict is PASS. The concern above is a carry-forward design
question for M6 planning, not an M4 defect requiring a retry cycle.
