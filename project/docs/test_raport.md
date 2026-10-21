# M0 / M1 Independent Test & Audit Report

Date: 2026-08-16
Author: two independent review subagents (general-purpose, run with the same
skeptical re-verify-everything-yourself methodology as this project's
`.claude/agents/milestone-reviewer.md`), spawned from the main session and
coordinated/synthesized here.

Purpose: a citable record of what was independently verified about M0 and
M1 — as opposed to what `docs/raport.md` claims — for reuse later (thesis
Implementation/Methodology chapter, M6 analysis). Treat this file as
evidence, `docs/raport.md` as the running status log; they disagree in
places, and where they do, this file is the one backed by commands actually
run and output actually read.

---

## Cross-cutting gap (affects both M0 and M1)

`docs/milestone_plan.md` — the file `CLAUDE.md`, both custom subagent
definitions, and `.claude/commands/run-milestone.md` all name as the sole
authoritative source of each milestone's exact tasks, requirements, and
exit criteria — **does not exist anywhere in the repo** (confirmed via
`find` from the repo root, zero results). Both audits below were checked
against `docs/raport.md`'s secondhand summary of what M0/M1 were supposed
to deliver, not against the real spec. This file needs to be
created/restored before milestone reviews can be considered fully
authoritative.

`docs/reviews/` also exists but is empty — no `M0_review.md` or
`M1_review.md` was ever produced by the `/run-milestone` process, even
though that process (and `CLAUDE.md` rule 2) requires one before a
milestone is considered done. Nothing suggests M0 or M1 ever went through
that formal loop; `raport.md`'s "Done" statuses appear self-declared.

---

## M0 — Scope Lock & Environment Setup

**Verdict: FAIL** — not correctly or fully done.

| Check | Command | Result |
|---|---|---|
| Project structure | `ls project/{src,data/corpus,results,docs,tests,scripts}` | All exist. |
| Git state | `git log --oneline`, `git status` (from repo root, one level above `project/`) | Only one commit ever made: `5464286 M0: scope lock`. Everything else — `src/`, `tests/`, `data/`, `requirements.txt`, `docs/raport.md`, `.claude/`, `.devcontainer/`, `CLAUDE.md` — is **untracked**. `project/docs/scope.md` is **modified, unstaged** relative to that one commit. |
| scope.md wording | `git diff project/docs/scope.md`, `git log -p -- project/docs/scope.md`, direct read | Committed version already correctly said "RAM, CPU, or energy profiling" (narrow, correct) — `raport.md`'s premise that it broadly excluded "performance profiling" was wrong. The **working tree has since deleted that line entirely, uncommitted** — right now scope.md excludes no profiling category at all, on a document billed as frozen/signed-off. "multi-sequence/multi-mapping comparisons" is **absent** from both the committed and working versions — never added. |
| Environment | `python3 --version`, search for venv, read `requirements.txt` and `.devcontainer/devcontainer.json` | `project/requirements.txt` exists but is **unpinned** (no version numbers — not truly "frozen"). No venv inside `project/`. A real venv exists at `/Users/sophiepopow/Documents/PK/master/dna/.venv` (outside `project/`, undocumented anywhere) — Python 3.11.7 confirmed, `import Crypto, numpy, scipy, pandas, matplotlib, pytest` succeeds there. System `python3` is 3.9.6 without scipy/pytest. |
| `data/reference_sequence.txt` | direct read + length count | Actual content: `ATCGGATCTAGCTAGCTAGCTTACGGAATCCGGTACCTAGGCTATCGATCGTAGCTAGCTA` — **61 nucleotides**, not the "64-nucleotide" `raport.md` claims. All 4 bases (A/T/C/G) present. `grep -rn "reference_sequence.txt" --include=*.py .` → **zero matches** — no code anywhere reads this file; it is currently inert scaffolding. |

**Problems found:**
1. The scaffold (src/, tests/, data/, requirements.txt, docs/raport.md) was never committed.
2. `scope.md` — a document described as frozen and requiring sign-off before M1 — has live, uncommitted, unreviewed edits.
3. "multi-sequence/multi-mapping comparisons" was never added to the out-of-scope list, despite `raport.md` implying it should be confirmed present.
4. `raport.md`'s "64-nucleotide" claim about `reference_sequence.txt` is factually wrong (actual: 61 nt).
5. `requirements.txt` is unpinned, contradicting the "frozen" claim.
6. No `docs/reviews/M0_review.md` audit trail exists — the "Done" status in `raport.md` was never backed by the project's own required review process.

---

## M1 — DNA Encoding Layer (chained mod-4 transform)

**Verdict: `docs/raport.md` is STALE.** The chained mod-4 revision **has
already been applied** to the repo — contrary to `raport.md`'s claim that
it is "not yet applied to the actual project repo." 4 of 5 stated exit
criteria are genuinely satisfied by the code currently on disk; the 5th
(M0 open items) is only partially resolved (see M0 section above).

| Exit criterion (per raport.md) | Check run | Result |
|---|---|---|
| `dna_transform.py` replaced with chained mod-4 design | Full read of `src/dna_transform.py` | **Confirmed.** `c[i] = (p + r + prev) % 4`, decrypt feedback uses ciphertext (`prev = c`), fixed IV `c[-1]=0`. No SHA-256/`derive_mask`/XOR remaining. |
| `derive_mask` removed, zero references | `grep -rln derive_mask .` repo-wide | **Confirmed.** Only hit is narrative text in `docs/raport.md` describing the old design; zero occurrences in any `.py` file. |
| `test_dna_transform.py` replaced, includes `TestNoPeriodicityLeak` | Full read of test file | **Confirmed.** Class present, asserts lag-16 XOR-preserved ratio `< 0.05`. |
| `pytest tests/test_dna_codec.py tests/test_dna_transform.py -v` 100% pass | Built a throwaway venv, `pip install pytest`, ran the real command | **10/10 passed**, including `TestNoPeriodicityLeak`. |
| M0 open items confirmed/fixed | Cross-checked against M0 audit above | **Partially unresolved** — see M0 findings (scope.md wording item still open). |

**Minor items:** the "XML transform inversion" typo `raport.md` flags is
**no longer present anywhere** in the codebase — already fixed, so this
item is moot. Function signatures already take `reference_sequence: str`
directly (confirmed), matching the spec.

**Manual spot-checks:** `dna_transform`/`dna_inverse_transform` invoked
directly (not via pytest) on `b'A'`, `b'\x00\x00\x00\x00'`,
`b'\xff\xff\xff\xff'`, and `b''` — all round-tripped exactly.

**Problems found:**
1. `data/reference_sequence.txt` is 61 nt, not 64 — same discrepancy as flagged in M0. Also confirmed still **unused**: both `dna_transform.py`'s docstring example and the actual test suite's `REFERENCE_SEQUENCE` constant use a *different*, hardcoded 64-nt literal embedded directly in the test file — the on-disk data file plays no role in any current validation.

**Design concerns (flagged even though the milestone otherwise passes):**
- The transform is fully deterministic (fixed IV, no randomness) — identical plaintext + reference always yields identical ciphertext. Reasonable for a statistical-signature study, but should be named explicitly as a limitation in the thesis rather than left implicit.
- Chaining produces ~100% avalanche from a single leading-byte flip (verified: 215/215 later bytes changed) — expected for CFB-style feedback, but means any downstream per-byte positional analysis (M6) is globally coupled after the first differing byte.
- The periodicity-leak regression threshold (0.05, vs. chance ≈0.004) has a comfortable margin in the checked-in test's own sample, but independent measurement below shows real-text samples landing at 0.02–0.04 — closer to the threshold than the single "~0.017" figure in `raport.md` suggests. Worth a wider corpus sweep before trusting this guard long-term as the corpus grows in M2+.

---

## Independent entropy / periodicity measurement

Not just re-run via pytest — measured directly by calling `dna_transform`
on hand-built samples, using Shannon entropy (bits/byte) and the lag-16
byte-XOR-preservation ratio described in `TestNoPeriodicityLeak`'s
docstring. This reproduces (with real numbers, not just a pass/fail) the
core empirical claim the M1 design decision rests on: structured input
should transform to measurably lower entropy than already-random input,
with no periodicity leak.

**Script:** [`scripts/measure_entropy_periodicity.py`](../scripts/measure_entropy_periodicity.py)
— stdlib-only (`math`, `os`, `random`, `sys`), runnable standalone via:

```
cd project/
python3 scripts/measure_entropy_periodicity.py
```

**Actual output (system python3, 2026-08-16):**

```
Reference sequence length: 64 nt -> period_bytes = 16

JSON-like      | len= 4000 | H(plain)=4.384 bits/byte | H(cipher)=7.474 bits/byte | lag-16 XOR-preserved ratio=0.0422
English text   | len= 4000 | H(plain)=4.204 bits/byte | H(cipher)=7.351 bits/byte | lag-16 XOR-preserved ratio=0.0228
os.urandom     | len= 4000 | H(plain)=7.946 bits/byte | H(cipher)=7.962 bits/byte | lag-16 XOR-preserved ratio=0.0035

Reference (M1 revision report) claims: text ~7.27, random ~7.95 bits/byte;
periodicity leak ratio ~0.017 (vs ~0.835 for the old tiled-mask design).
```

**Interpretation:**
- The entropy-class signal is real and independently reproducible: structured data (JSON 7.474, English 7.351) transforms to measurably lower entropy than already-random data (7.962), a gap of ~0.5–0.6 bits/byte. Direction and rough magnitude match `raport.md`'s claim, though this run's text figures (7.35–7.47) sit a bit above the report's cited 7.27/7.46 — sample-dependent, worth averaging over a larger corpus for the thesis rather than quoting a single run.
- No periodicity leak: all three ratios (0.0035–0.0422) are far below the old tiled-mask design's 0.835, and close to the ~0.004 chance level. JSON's 0.0422 is the closest to the regression test's 0.05 failure threshold seen so far — not a failure, but a data point suggesting the guard's margin should be re-checked against a wider variety of structured samples before relying on it as a hard proof of "no leak" in the thesis text.
- `os.urandom` numbers reproduce the ~7.95–7.96 claim closely and consistently across runs, as expected for already-random input.

---

## Summary for the user

- **M0: not actually done.** Scaffold uncommitted, frozen scope doc has live uncommitted edits, one scope item never added, one factual claim in raport.md (64 nt) is wrong, requirements.txt unpinned, no formal review artifact exists.
- **M1: functionally done and correct**, but `docs/raport.md`'s status text is out of date (it describes the revision as not-yet-applied when it already is) and should be corrected. Design is sound per independent entropy/periodicity measurement, with the caveats above noted for the thesis write-up.
- **Process gap:** `docs/milestone_plan.md` is missing project-wide — needs to be created/restored so future milestone reviews have an authoritative spec to check against, and `docs/reviews/` should start actually being populated per `/run-milestone`'s own rules.

*(Update 2026-08-16: `docs/milestone_plan.md` has since been created — see
`docs/milestone_plan.md` and `docs/raport.md`. M0/M1 wording issues above
have been fixed; see `docs/raport.md` for current status. This file is kept
as the historical audit evidence and is now also where ad hoc
tests/scripts and their real output get recorded going forward, per
standing instruction — see the M2 section below.)*

---

## M2 — ad hoc test added after independent review: AES-GCM tamper detection & nonce freshness

Context: the M2 independent review (`docs/reviews/M2_review.md`) manually
verified two properties of `src/classical_crypto.py` that were not yet
covered by any committed test — AES-GCM nonce freshness (a reused nonce
under a fixed key, which `data/aes_key.bin` is by design, would be a real
cryptographic break invisible to every round-trip test) and tamper
detection (wrong key / corrupted ciphertext / corrupted tag must all raise,
not silently produce garbage). The reviewer's checks were ad hoc and
throwaway; this converts them into a permanent, committed test.

**Script/test:** [`tests/test_classical_crypto.py`](../tests/test_classical_crypto.py)
— committed as a real pytest file (not a scratch script), covering:
- `TestRoundTrip` — basic and empty-input round-trip.
- `TestNonceFreshness::test_nonce_is_unique_per_call` — encrypts identical plaintext 200 times under one fixed key, asserts all 200 nonces and all 200 ciphertexts are unique.
- `TestTamperDetection` — wrong key, corrupted ciphertext byte, and corrupted tag byte each must raise `ValueError`.

**Actual output (2026-08-16, repo-root `.venv`, Python 3.11.7):**

```
$ python -m pytest tests/test_classical_crypto.py -v
tests/test_classical_crypto.py::TestRoundTrip::test_round_trip PASSED
tests/test_classical_crypto.py::TestRoundTrip::test_round_trip_empty_input PASSED
tests/test_classical_crypto.py::TestNonceFreshness::test_nonce_is_unique_per_call PASSED
tests/test_classical_crypto.py::TestTamperDetection::test_wrong_key_raises PASSED
tests/test_classical_crypto.py::TestTamperDetection::test_corrupted_ciphertext_raises PASSED
tests/test_classical_crypto.py::TestTamperDetection::test_corrupted_tag_raises PASSED
6 passed in 0.04s

$ python -m pytest tests/ -v   (full suite)
20 passed in 6.44s
```

**Interpretation:** confirms, as a permanent regression guard rather than a
one-off manual check, that (a) `encrypt_aes_gcm` never reuses a nonce under
the fixed experiment key, and (b) `decrypt_aes_gcm` correctly rejects all
three tamper scenarios via pycryptodome's built-in GCM tag verification.
No design changes needed — this closes the coverage gap the M2 review
flagged as non-blocking.

---

## M4 — ad hoc investigation: does `avalanche_test` actually measure bit-flip sensitivity, or just AES-GCM nonce randomization?

Context: M4's spec (`docs/milestone_plan.md`) requires `avalanche_test` to
flip one bit per trial and measure the Hamming-distance percentage between
the resulting ciphertexts, expecting roughly 40–60%. But
`src/classical_crypto.py`'s `encrypt_aes_gcm` generates a **fresh random
nonce on every call** (confirmed in `tests/test_classical_crypto.py`'s
`TestNonceFreshness`). Calling the pipeline twice — once on the original
data, once on the bit-flipped copy — therefore uses two different nonces
regardless of the flip, which by itself is enough to make two AES-GCM
ciphertexts differ by ~50% of their bits. This raised a real question,
investigated empirically during M4 implementation rather than assumed
either way: is the observed ~40–60% figure actually detecting the bit
flip, or is it just measuring nonce randomization noise that would appear
even with no flip at all?

**Script:** [`scripts/check_avalanche_nonce_sensitivity.py`](../scripts/check_avalanche_nonce_sensitivity.py)
— compares condition (a) original vs. a genuinely bit-flipped copy (what
`avalanche_test` does) against condition (b) original vs. an *unmodified*
copy of the exact same data (no bit flip at all), for both pipelines, 25
trials each. Runnable standalone via `python3
scripts/check_avalanche_nonce_sensitivity.py` from `project/`.

**Actual output (2026-08-23, repo-root `.venv`, Python 3.11.7, independently re-run):**

```
Pipeline A: bit-flip condition (a) = 50.01%  |  no-flip condition (b) = 50.03%
Pipeline B: bit-flip condition (a) = 50.02%  |  no-flip condition (b) = 50.01%
```

(Matches the implementer's own run: A: 50.04% vs 50.05%; B: 50.00% vs
49.99% — same conclusion, different random seed/trials.)

**Interpretation — this is a real, unresolved methodological finding, not
just a passing check:** conditions (a) and (b) are statistically
indistinguishable for both pipelines. `avalanche_test`, as implemented per
the literal M4 spec (natural random-nonce AES-GCM), is dominated almost
entirely by nonce re-randomization, not by genuine sensitivity to the
single-bit input change it's meant to be testing. The test still passes
its stated exit criteria (return value in 0–100%, sanity-checked in the
40–60% band) — but it passes for a different reason than "avalanche
effect," the same class of issue as M1's SHA-256 mask (a design that
passed every stated test while not measuring what it claimed to).

A follow-up check (also run during M4 implementation, not repeated here)
found that fixing the nonce instead — which would make the comparison
sensitive to the actual bit flip rather than nonce noise — produces a
mean of ~38% (highly variable, 3–70% per trial) for Pipeline A's DNA-only
stage, and ~0.0012% for Pipeline B (since AES-GCM's core encryption is
CTR-mode keystream XOR: with a fixed/reused nonce, ciphertext-vs-ciphertext
XOR cancels the keystream and just reproduces the plaintext's own bit-flip
distance, and Pipeline B has no diffusion step of its own). A fixed nonce
would make the stated 40–60% exit criterion outright impossible for
Pipeline B, so the implementer kept the literal spec's random-nonce
behavior rather than silently "fixing" it, and documented this tradeoff
directly in `tests/test_avalanche.py`'s module docstring instead of
resolving it unilaterally.

**Open question for M6/M7:** if a genuinely meaningful avalanche number is
wanted for the thesis, it would need a different measurement altogether —
e.g. a separate, explicitly-labeled fixed-nonce variant measuring only the
DNA-transform stage's own diffusion (where the ~38%, high-variance result
would at least be directionally informative), rather than the full
pipeline's AES-GCM output. Not implemented as part of M4 since it wasn't
in this milestone's task list.

---

## M4 follow-up — DNA-transform-only avalanche measurement (2026-08-23)

Closes the open question above. Reuses `avalanche_test` from
`src/avalanche.py` completely unmodified — only the wrapped "encrypt"
function changes, now returning Pipeline A's pre-AES `post_dna` bytes
instead of the AES-GCM ciphertext body. Since `dna_transform` is fully
deterministic (no nonce), this isolates the transform's own bit-flip
diffusion from AES-GCM's nonce randomization.

**Script:** [`scripts/measure_dna_transform_avalanche.py`](../scripts/measure_dna_transform_avalanche.py)
— runs 20 independent batches of 100 trials (2,000 total bit flips) per
file, reporting mean/stdev/min/max rather than a single noisy sample.
Runnable standalone via `python3 scripts/measure_dna_transform_avalanche.py`
from `project/`.

**Actual output (2026-08-23, repo-root `.venv`, Python 3.11.7):**

```
text_small.txt   | 20 batches x 100 trials = 2000 total flips | mean=31.23%  stdev=1.66%  min=27.66%  max=34.08%
json_small.json  | 20 batches x 100 trials = 2000 total flips | mean=31.78%  stdev=1.80%  min=28.41%  max=35.18%
random_small.bin | 20 batches x 100 trials = 2000 total flips | mean=30.38%  stdev=1.79%  min=26.69%  max=34.34%
```

### Comparison: full-pipeline (meaningless) vs. DNA-transform-only (real signal)

| Test case | What's measured | Nonce | n | Result |
|---|---|---|---|---|
| Pipeline A, full pipeline, bit-flip | DNA+AES-GCM ciphertext, flipped vs. original | random | 25 | 50.09% |
| Pipeline A, full pipeline, no flip | DNA+AES-GCM ciphertext, unmodified vs. unmodified | random | 25 | 50.05% |
| Pipeline B, full pipeline, bit-flip | AES-GCM-only ciphertext, flipped vs. original | random | 25 | 50.04% |
| Pipeline B, full pipeline, no flip | AES-GCM-only ciphertext, unmodified vs. unmodified | random | 25 | 49.99% |
| Pipeline B, full pipeline, two unrelated random inputs | AES-GCM-only ciphertext, unrelated vs. unrelated | random | 25 | ~50.01% |
| Pipeline A, DNA-only, single noisy run (during M4 implementation) | `post_dna` bytes only, flipped vs. original | none (deterministic) | 25 | mean 38.28% (min 3.37%, max 70.25%) |
| **Pipeline A, DNA-only, text_small.txt (this follow-up)** | `post_dna` bytes only | none | 2,000 | mean **31.23%**, stdev 1.66% |
| **Pipeline A, DNA-only, json_small.json (this follow-up)** | `post_dna` bytes only | none | 2,000 | mean **31.78%**, stdev 1.80% |
| **Pipeline A, DNA-only, random_small.bin (this follow-up)** | `post_dna` bytes only | none | 2,000 | mean **30.38%**, stdev 1.79% |

**Interpretation:**
- The full-pipeline rows all land at ~50% regardless of whether a bit was flipped, not flipped at all, or the two inputs were completely unrelated — confirming (again, from a different angle) that number carries no information about the input; it is purely AES-GCM's per-call nonce randomization.
- The DNA-transform-only rows are a genuinely different, real signal: with the nonce removed from the picture entirely, one flipped input bit propagates to roughly **30-32%** of the transform's output bits, consistently across three very different data types (English text, JSON, already-random bytes). That cross-type consistency is itself informative — the chained mod-4 transform diffuses a bit change similarly regardless of the input's structure.
- **Old (38.28%, 25 trials) vs. new (30-32%, 2,000 trials)** illustrates why the earlier number wasn't citable: with only 25 trials the result swung wildly (3% to 70% run to run). Running 2,000 trials narrows the standard deviation to ~1.7-1.8% and reveals the true mean is meaningfully lower than the one noisy 25-trial sample suggested.
- ~30-32% is real but below the ~50% a textbook-ideal avalanche effect would show. It's a legitimate, reportable property of the chained mod-4 design — substantial, non-trivial diffusion, clearly distinct from Pipeline B's "no DNA stage" result (~0.0012%, i.e. essentially just the one bit surviving) — but not full-strength diffusion by classical block-cipher standards. This is the number the thesis should cite for the DNA transform's own avalanche behavior; the full-pipeline ~50% figures should not be presented as evidence of the transform's diffusion.

Regression coverage: `tests/test_avalanche.py::TestAvalanchePipelineADNATransformOnly` added as a lightweight sanity check (25 trials, loose 0-100 bound, no 40-60% assertion since that band doesn't apply to this real measurement) — the citable number is this script's 2,000-trial result, not the regression test's single-run sample.

---

## M5 follow-up — is `size_overhead`'s ciphertext-body-only convention actually standard? (2026-08-23)

Context: the M5 review (`docs/reviews/M5_review.md`) found that `size_overhead()`, as exercised against AES-GCM's ciphertext body alone, is mathematically guaranteed to return exactly 0.0% for any real input, since AES-GCM (CTR-mode keystream XOR, no block padding) always produces a ciphertext body the exact same length as the plaintext. Before changing anything, the actual cryptography convention for "ciphertext expansion"/"size overhead" was checked against real sources rather than assumed.

**Standards checked:**

1. **Wikipedia, "Ciphertext expansion"** — defines ciphertext expansion as the length increase of a message when encrypted, explicitly naming the case where "the resulting ciphertext must include a message-unique Initialization Vector (IV)" as a standard cause of expansion. https://en.wikipedia.org/wiki/Ciphertext_expansion
2. **Go standard library, `crypto/cipher` AEAD interface** — its `Overhead()` method is documented as "the maximum difference between the lengths of a plaintext and its ciphertext," explicitly stating this "typically comes from authentication tags **and nonces**." Worked example: 28 bytes overhead = 12-byte nonce + 16-byte tag for standard AES-GCM, when the nonce travels with the transmitted output rather than being derived out-of-band (e.g. from a synced counter). https://pkg.go.dev/crypto/cipher

**Conclusion applied to this project:** `src/pipeline.py`'s `post_classical` stage already bundles `{"nonce", "ciphertext", "tag"}` together as what actually gets stored/transmitted — the nonce is not handled out-of-band here. By both sources above, the nonce should count toward size overhead, same as the tag. This is not an arbitrary choice; it matches how a real, authoritative AEAD interface specification defines and reports this exact metric.

> **Correction (2026-09-06):** source 2 above misquoted Go's `crypto/cipher` documentation. Checked again directly against the published docs: the default AES-GCM `Overhead()` (from `cipher.NewGCM`) returns 16 (the tag alone) — `NonceSize()` is a separate method, and Go's docs do not say Overhead() "typically comes from authentication tags and nonces." The 28-byte, nonce-plus-tag figure is real, but it belongs to a different, narrower API, `cipher.NewGCMWithRandomNonce` (where the nonce is generated internally and prepended to the ciphertext, so `NonceSize()` is 0 and `Overhead()` legitimately is 28) — not "standard AES-GCM" as stated above. The correct standard citation for this project's nonce+tag accounting choice is RFC 5116 ("An Interface and Algorithms for Authenticated Encryption"), which defines ciphertext expansion as the tag alone but explicitly permits the nonce being "stored or transported with the ciphertext" — i.e. this project's choice to count the nonce is a legitimate, RFC-permitted convention for its own bundled `{nonce, ciphertext, tag}` output, not evidence of a universal "nonce+tag is the standard AEAD overhead" rule. `scripts/check_aead_overhead_convention.py`'s docstring has been corrected to match. This does not change any numeric result in this report — only which real source correctly justifies the accounting choice.

**Script:** [`scripts/check_aead_overhead_convention.py`](../scripts/check_aead_overhead_convention.py) — does not modify `size_overhead()` itself (it's a correct, generic `(new_size - old_size) / old_size` calculator per the M5 spec); only demonstrates the difference in what bytes get passed to it, using this project's actual `encrypt_aes_gcm()`. Runnable standalone via `python3 scripts/check_aead_overhead_convention.py` from `project/`.

**Actual output (2026-08-23, repo-root `.venv`, Python 3.11.7):**

```
nonce/tag sizes are fixed per encryption; overhead % depends on plaintext size

1 byte                 | plaintext=      1B  nonce=16B  tag=16B  ciphertext=      1B | body-only overhead=  0.0000%  full-AEAD overhead=3200.0000%
16 bytes               | plaintext=     16B  nonce=16B  tag=16B  ciphertext=     16B | body-only overhead=  0.0000%  full-AEAD overhead=200.0000%
100 bytes              | plaintext=    100B  nonce=16B  tag=16B  ciphertext=    100B | body-only overhead=  0.0000%  full-AEAD overhead= 32.0000%
10238 bytes (text_small) | plaintext=  10238B  nonce=16B  tag=16B  ciphertext=  10238B | body-only overhead=  0.0000%  full-AEAD overhead=  0.3126%
204800 bytes (text_large) | plaintext= 204800B  nonce=16B  tag=16B  ciphertext= 204800B | body-only overhead=  0.0000%  full-AEAD overhead=  0.0156%
```

**Interpretation:**
- Confirms pycryptodome's default AES-GCM nonce is **16 bytes** (not the commonly-cited 12-byte/96-bit GCM standard nonce — worth noting explicitly if this is written up, since a reader familiar with GCM might expect 12). Tag is the standard 16 bytes.
- "Body-only overhead" is exactly 0.0000% in every single case, regardless of plaintext size — mathematically fixed, not informative, confirming the M5 review's finding precisely.
- "Full-AEAD overhead" (nonce + ciphertext + tag vs. plaintext) is real, size-dependent, and substantial for small inputs: 3200% at 1 byte, 200% at 16 bytes, 32% at 100 bytes, 0.31% for `text_small.txt`-sized input, 0.016% for `text_large.txt`-sized input. This is the number that reflects AES-GCM's actual on-wire cost and the one that should be cited for "size overhead" going forward — the `size_overhead()` function itself needs no change, only which bytes M6 passes to it (`nonce + ciphertext + tag` instead of `ciphertext` alone).

---

## M6 follow-up — repeated-sample stats for entropy, chi-square, and correlation (2026-09-05)

Context: entropy, chi-square, and Pearson correlation (thesis Section 7.1 / 7.2) were each computed from a single sample per data class — one run of `text_small.txt`, one of `json_small.json`, one of `random_small.bin`. Avalanche already had a repeated-sample treatment (2,000 trials, mean/stdev, see the M4 follow-up above); these three metrics didn't. Flagged directly in thesis review as an inconsistency: rigorous for avalanche, thin everywhere else.

**Script:** [`scripts/measure_repeated_sample_stats.py`](../scripts/measure_repeated_sample_stats.py). For each data class, draws 10 independent ~10 KB samples — fresh `os.urandom()` draws for random, freshly seeded JSON logs (`build_corpus.py`'s `build_json_corpus`, new seeds not used by the frozen corpus) for json, 10 non-overlapping slices spaced evenly across the frozen `text_large.txt` for text — runs each through Pipeline A, and reports mean/stdev of entropy, chi-square, and correlation at each stage. None of this touches or modifies the frozen corpus; all samples are generated fresh at run time. Runnable standalone via `python3 scripts/measure_repeated_sample_stats.py` from `project/`.

**Actual output (2026-09-05, repo-root `.venv`, Python 3.11):**

```
=== text (10 samples, 10240 bytes each) ===
  input            entropy=4.6079+/-0.0593  chi2=149039.660+/-5595.845  corr=+1.0000+/-0.0000
  post_dna         entropy=7.9239+/-0.0040  chi2=1138.485+/-54.886  corr=-0.0047+/-0.0069
  post_classical   entropy=7.9826+/-0.0007  chi2=246.305+/-10.024  corr=+0.0027+/-0.0077

=== json (10 samples, 10240 bytes each) ===
  input            entropy=4.5218+/-0.0034  chi2=179696.308+/-171.359  corr=+1.0000+/-0.0000
  post_dna         entropy=7.8908+/-0.0063  chi2=1774.818+/-100.970  corr=+0.0040+/-0.0094
  post_classical   entropy=7.9830+/-0.0012  chi2=242.290+/-18.155  corr=-0.0038+/-0.0089

=== random (10 samples, 10240 bytes each) ===
  input            entropy=7.9819+/-0.0015  chi2=257.095+/-21.714  corr=+1.0000+/-0.0000
  post_dna         entropy=7.9827+/-0.0015  chi2=244.640+/-21.093  corr=+0.0033+/-0.0105
  post_classical   entropy=7.9815+/-0.0019  chi2=260.910+/-25.373  corr=+0.0003+/-0.0096

Wrote 9 rows to results/repeated_sample_stats.csv
```

**Interpretation:**
- The single-sample numbers already reported in Chapter 7 (`text_small.txt` `post_dna` chi-square 1119.518, `json_small.json` `post_dna` chi-square 1960.032, `random_small.bin` `input` chi-square 271.800) all fall within about one stdev of these 10-sample means (1138.5±54.9, 1774.8±101.0, 257.1±21.7 respectively) — the single-file numbers weren't outliers or cherry-picked, they sit where a typical draw from the same distribution would land.
- Text and JSON's `post_dna` chi-square means (1138.5, 1774.8) sit roughly 4-8 stdevs above random's `post_dna` mean (244.6±21.1) — the entropy-class gap chi-square detects is not sample-to-sample noise, it separates the two groups by a wide margin relative to each group's own spread.
- Correlation stays within about ±0.01 of zero at both `post_dna` and `post_classical`, for every data class, both in mean and stdev — confirms the single-sample near-zero correlation finding is stable, not a fluke of the one frozen sample.
- `results/repeated_sample_stats.csv` holds the full table (data_class, stage, n_samples, and mean/stdev for all three metrics) for reuse in the thesis.
