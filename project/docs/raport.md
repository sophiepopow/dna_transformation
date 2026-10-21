# Project Status Report — DNA Encoding Impact on Lightweight Encryption

Last updated: 2026-08-25 (added `docs/related_work_dna_lwcs.md`, a
pre-M7 related-work note — see below)
Purpose: single source of truth for any agent picking up this project —
read this before touching M0-M6 code or starting M7.

**Pre-M7 prep:** `docs/related_work_dna_lwcs.md` — a full read of the
actual DNA-LWCS paper (Aqeel et al. 2025, the M2/M6 reference paper),
comparing its architecture and metrics against this project's, and
explaining why AES-GCM was deliberately substituted for ECC. Ready to
drop into M7's `02_related_work.md` and `07_limitations.md` chapters.

## Current Gate

**M0-M6 are all DONE.** M6 — the full experimental run — passed
independent review on its first cycle. This is the most consequential
milestone so far: it ran the real pipelines against the real frozen
corpus and real reference sequence for the first time, and in doing so
**revised the magnitude of this project's central finding**. See the M6
section below before citing any pre-M6 entropy numbers in the thesis.
Both M4/M5 carried-forward decisions (avalanche measured per-stage;
size overhead computed both ways) were resolved and correctly implemented
in M6's experiment script — see below.

An independent audit (`docs/test_raport.md`) previously found this file
stale for M0/M1; that history is preserved below. Note: this project is
**not using git** for the rest of the project — M3 was a deliberate,
narrow, one-time exception to prove the corpus is frozen via `git tag
corpus-v1-frozen`; M0's git-commit item remains not applicable as before.

## Milestone Status

| Milestone | Status | Blocking? |
|---|---|---|
| M0 | Done | No |
| M1 | Done, revision applied and verified — **entropy-gap magnitude corrected by M6, see below** | No |
| M2 | Done, passed independent review | No |
| M3 | Done, passed independent review | No |
| M4 | Done, passed independent review — avalanche caveat resolved in M6 | No |
| M5 | Done, passed independent review — size_overhead caveat resolved in M6 | No |
| M6 | Done, passed independent review — **entropy-gap magnitude corrected, see below** | No |
| M7 | Not started | |

---

## M0 — Scope Lock & Environment Setup

**Completed:**
- Project structure created: `project/src/`, `project/data/corpus/`, `project/results/`, `project/docs/`, `project/tests/`, `project/scripts/`
- `docs/scope.md` written with: research question verbatim, 3 data classes, 2 pipelines, out-of-scope list, NIST SP 800-22 scope-boundary caveat
- Python 3.11.7 venv available (repo root `.venv`, not `project/.venv` — harmless path deviation from the literal spec); `pycryptodome`, `numpy`, `scipy`, `pandas`, `matplotlib`, `pytest` all import cleanly from it
- Import checks passed for `Crypto`, `numpy`, `scipy`
- `docs/milestone_plan.md` now exists (converted from `docs/dna_plan.pdf`, which was the actual plan all along under the wrong filename/format)

**Resolved by the 2026-08-16 audit + fixes:**
1. ~~Git commit unconfirmed.~~ Not applicable — this project is not using git for now, by explicit decision. Not treated as an open defect.
2. **`scope.md` out-of-scope wording — fixed.** "RAM, CPU, or energy profiling" (narrow, correct) is now present; "Multi-sequence/multi-mapping comparisons" was added (it was missing entirely before). The Pipelines section was also wrong and has been corrected: it previously described "DNA-only" vs. "DNA+classical," but the plan's actual pipelines are "DNA+AES-GCM" (Pipeline A) vs. "AES-GCM only, no DNA" (Pipeline B, the control). Both are now correct in `docs/scope.md`.
3. **`data/reference_sequence.txt` provenance confirmed** — hardcoded, not network-fetched. Its actual length is **61 nucleotides**, not "64" as this file previously claimed (see M1 section below) — 61 is within the plan's required 40–200 nt range, so this was a documentation error, not a spec violation.

**Still open, non-blocking:** `requirements.txt` is a hand-written unpinned package list rather than real `pip freeze` output. Left as-is by explicit decision — not worth the churn of a full reinstall for a criterion this project isn't currently pressed on.

---

## M1 — DNA Encoding Layer

**Unchanged, working, no action needed:**
- `src/dna_codec.py` — `bytes_to_bits`, `bits_to_dna`, `dna_to_bits`, `bits_to_bytes`. Round-trip tested and passing, including on multi-byte UTF-8 (Japanese text) and binary samples. Keep as-is.
- `data/reference_sequence.txt` — fixed **61**-nucleotide sequence (corrected from this report's earlier, wrong "64-nucleotide" claim), all 4 bases represented, within the plan's required 40–200 nt range. Keep as-is. Note: it is not currently read by any code — both `dna_transform.py`'s docstring example and `tests/test_dna_transform.py`'s `REFERENCE_SEQUENCE` constant use a separate, hardcoded 64-nt literal. Wiring this file into the actual pipeline is expected to happen at M2, not before.

**Superseded — do not use the original `dna_transform.py`:**
The original implementation used `derive_mask()` (SHA-256-based keystream) + XOR + a fixed 3-bit rotation.

**Why it was revised:**
A SHA-256-derived mask is cryptographically strong. XOR-ing *any* input against it — regardless of the input's original entropy — produces near-maximal-entropy output. Measured: text and JSON both converged to ~7.96 bits/byte after the transform, statistically indistinguishable from already-random data (~7.96 bits/byte). This erases the entropy-class signal the thesis is designed to detect, since the M6 analysis depends on structured data (text/JSON) behaving differently from already-random data at the DNA-transform-only stage.

A simpler intermediate fix (tiling the reference sequence directly instead of hashing it) was tested next and failed differently: the ciphertext preserved an exact, deterministic relationship between plaintext bytes 16 apart (the mask's period). Ciphertext-only autocorrelation at lag 16 measured **0.835** on structured text (vs ~0.01 for random data) — a severe, trivially detectable artifact, structurally identical to a classic repeating-key XOR cipher weakness.

**Final design — chained mod-4 nucleotide addition** (no cryptographic primitive, no static mask):
c[i] = (plain[i] + ref[i mod len(ref)] + c[i-1]) mod 4

Each output nucleotide depends on the entire preceding stream, not just its position modulo the reference sequence's length. Measured result: periodicity leak resolved (autocorrelation dropped to ~0.017, back to chance level), while a real entropy gap is preserved between structured and random data (text 7.27 vs random 7.95 bits/byte; JSON 7.46 vs 7.95).

> ### ⚠️ Correction from M6 (2026-08-23): the numbers above used a sample reference sequence, not the real one
>
> The 7.27/7.46 vs 7.95 figures above were measured with a **64-nt literal
> hardcoded directly in `scripts/measure_entropy_periodicity.py` and
> `tests/test_dna_transform.py`** — never the actual frozen
> `data/reference_sequence.txt` (61 nt) that every real pipeline run since
> M2 has actually used. M6's full experimental run, using the real
> reference sequence against the real frozen corpus for the first time,
> found the **real gap is only ~0.05-0.10 bits/byte** (e.g. `text_small.txt`:
> 7.9265 post-DNA vs. random's 7.9804) — much smaller than implied above.
>
> This is not a bug: M6's independent reviewer isolated the cause via
> controlled swaps and found it's the reference sequence itself. The real
> 61-nt sequence is almost perfectly base-balanced (A:15/T:16/C:15/G:15)
> and contains five repeats of `AGCT` — a perfect period-4 cycle through
> all four mod-4 values under the default mapping — making it a much more
> effective "mixer" under the chained mod-4 design than the skewed 64-nt
> sample literal above (A:20 vs G:10, with same-letter runs) ever was.
> Swapping the real corpus through the *sample* reference sequence
> reproduces a 0.22-bit gap; swapping the *sample* text through the real
> reference reproduces something close to the small M6 gap — confirming
> the reference sequence, not the corpus or the transform's correctness,
> drives the difference. See `docs/reviews/M6_review.md` for the full
> four-way isolation and `docs/raport.md`'s M6 section below for the
> real, citable numbers.
>
> **Entropy still isn't the strongest surviving signal at `post_dna`** —
> chi-square and compression ratio show a proportionally much clearer
> separation (chi-square ~4.8-8.4x random's, vs. entropy's <1% relative
> gap), for a legitimate statistical reason: entropy is a log-compressed
> summary that saturates near its maximum quickly, while chi-square stays
> sensitive to higher-order deviations from uniformity longer. **Use M6's
> numbers, not the ones above, anywhere this needs to be cited in the
> thesis.**

### M1 Revision — status: APPLIED and independently verified (2026-08-16)

All of the following were confirmed against the actual repo state, not
just claimed — see `docs/test_raport.md` for the full command-by-command
evidence and `docs/scripts/measure_entropy_periodicity.py` for the
reusable independent-measurement script:

1. ~~Replace `src/dna_transform.py`...~~ **Done.** Current file implements the chained mod-4 design (`c[i] = (p + r + prev) % 4`, ciphertext-feedback on decrypt, fixed IV). No SHA-256/XOR/rotation code remains.
2. ~~Delete `derive_mask` entirely...~~ **Done.** `grep -rln derive_mask` across the whole repo returns zero `.py` hits (only this narrative text still mentions the name).
3. ~~Replace `tests/test_dna_transform.py`...~~ **Done.** `TestNoPeriodicityLeak` regression guard is present and passing.
4. ~~Re-run pytest...~~ **Done.** `pytest tests/test_dna_codec.py tests/test_dna_transform.py -v` — **10/10 passed**, independently re-run (not just trusted from an earlier claim).
5. ~~Function signature changed...~~ **Confirmed.** Both functions take `reference_sequence: str` directly.

**Minor cleanup:** the "XML transform inversion" typo is no longer present anywhere in the codebase — already fixed, this item is moot.

The design deviation from the original written M1 spec (which called for
`derive_mask` + XOR + fixed rotation) is now formally documented as an
addendum in `docs/milestone_plan.md`'s M1 section, per project decision to
keep the original spec as historical record rather than silently rewrite
it.

**Independent entropy/periodicity re-measurement** (not just pytest —
actual Shannon entropy and lag-16 XOR-preservation ratio computed directly
on fresh samples via `scripts/measure_entropy_periodicity.py`):

```
JSON-like      | H(cipher)=7.474 bits/byte | lag-16 XOR-preserved ratio=0.0422
English text   | H(cipher)=7.351 bits/byte | lag-16 XOR-preserved ratio=0.0228
os.urandom     | H(cipher)=7.962 bits/byte | lag-16 XOR-preserved ratio=0.0035
```

Confirms the entropy-class signal is real (structured data lands ~0.5–0.6
bits/byte below random) and no periodicity leak exists (all ratios near
the ~0.004 chance level, far below the old design's 0.835). One design
concern worth carrying into the thesis write-up: the JSON sample's ratio
(0.0422) sits closer to the regression test's 0.05 failure threshold than
a single-sample figure suggests — worth a wider corpus sweep at M3/M6
rather than treating one number as proof the guard has a wide margin.

### M1 Revision — Exit Criteria (all pass)

- [x] `src/dna_transform.py` replaced with the chained mod-4 design
- [x] `derive_mask` removed, no remaining references anywhere in the codebase
- [x] `tests/test_dna_transform.py` replaced with the updated suite
- [x] `pytest tests/test_dna_codec.py tests/test_dna_transform.py -v` — 100% pass, including `TestNoPeriodicityLeak`
- [x] M0 open items confirmed or fixed (git commit item is not applicable — project isn't using git for now)

---

## M2 — Classical Encryption Layer & Pipeline Composition

**Implemented:**
- `src/classical_crypto.py` — `encrypt_aes_gcm(data, key) -> (nonce, ciphertext, tag)` and `decrypt_aes_gcm(nonce, ciphertext, tag, key) -> bytes`, both thin wrappers around pycryptodome's `AES.new(key, AES.MODE_GCM)`.
- `src/pipeline.py` — `pipeline_b_classical_only(data, key) -> dict` (stages: `input`, `post_classical`) and `pipeline_a_dna_plus_classical(data, key, reference_sequence) -> dict` (stages: `input`, `post_dna`, `post_classical`), plus `decrypt_pipeline_a(stages, key, reference_sequence)` and `decrypt_pipeline_b(stages, key)` that exactly invert them. The `post_classical` stage value is a dict `{"nonce", "ciphertext", "tag"}` so the pipeline result is self-contained for decryption.
- `data/aes_key.bin` — fixed 32-byte key, generated once via `os.urandom(32)` (did not exist before M2; confirmed not regenerated across repeated test runs by MD5 comparison).
- `tests/test_pipeline.py` — 20 random byte strings (10 bytes–200 KB, seeded) round-tripped through both pipelines; also asserts each pipeline's stage-key set. Loads `data/reference_sequence.txt` (61 nt) and `data/aes_key.bin` directly, per spec.
- Signature deviation (expected, per the M1 Revision addendum): Pipeline A's third parameter is named `reference_sequence: str`, not `mask: bytes` — matches M1's actual final `dna_transform`/`dna_inverse_transform` signature.

**Verified:** `pytest tests/ -v` — 14/14 passed (10 M1 + 4 M2). Manual REPL check confirmed byte-identical round-trip for both pipelines on a non-trivial sample and confirmed the exact stage-key sets (`{input, post_dna, post_classical}` for A, `{input, post_classical}` for B).

**Not done as part of M2 (out of scope):** no statistical measurement of `post_dna`/`post_classical` stage entropy — that's M4. No corpus files used yet — that's M3.

### M2 — Independent review: PASS (2026-08-16, first cycle, no retries)

Full checklist, commands, and design concerns in `docs/reviews/M2_review.md`. Summary of what the reviewer verified independently (not just re-running the implementer's own claims):

- Re-ran `pytest tests/test_pipeline.py -v` (4 passed) and the full suite (14 passed) itself.
- **Nonce freshness explicitly checked**, not assumed: encrypted identical plaintext 200 times under the fixed experiment key and confirmed 200 unique nonces/ciphertexts. A reused/deterministic GCM nonce would have been a real crypto break invisible to every round-trip test in the suite — this is exactly the "tests pass, design unsound" failure class M1's history warned about, and it checked out clean here.
- Manually confirmed AES-GCM correctly rejects a wrong key, a corrupted ciphertext byte, and a corrupted tag byte (all raise `ValueError: MAC check failed`) — sound, but **not currently covered by the committed test suite**. Recommended (non-blocking): add explicit tamper-detection tests before M4/M6 lean on this layer further.
  → **Closed 2026-08-16:** `tests/test_classical_crypto.py` added — nonce-freshness (200 unique nonces/ciphertexts under a fixed key) and tamper-detection (wrong key / corrupted ciphertext / corrupted tag all raise) are now permanent, committed tests. 6/6 pass, full suite now 20/20. See `docs/test_raport.md`'s M2 section for the script and real output.
- Confirmed `reference_sequence` is genuinely loaded from `data/reference_sequence.txt` and doing real work (`post_dna != input`), not a stub or a competing hardcoded literal.
- Confirmed `data/aes_key.bin` reuse (mtime + MD5 unchanged across a run) and the `mask`→`reference_sequence` rename's consistency independently, rather than trusting the implementer's own claims.
- Judged the decrypt-function signature deviation from the plan's literal one-argument pseudocode as justified: the literal spec can't actually work (decryption needs the key; Pipeline A needs the reference sequence too), and the actual design was confirmed genuinely invertible by direct invocation.

**No required fixes. Verdict: PASS.**

---

## M3 — Test Corpus Construction

**Implemented:**
- `scripts/build_corpus.py` — fetches Jane Austen's *Pride and Prejudice* (Project Gutenberg eBook #1342) live via `urllib.request`, slices to size starting at the novel's real opening line (skipping Gutenberg preface/front-matter), and generates 6 corpus files: `text_small.txt`/`text_large.txt` (real English prose), `json_small.json`/`json_large.json` (synthetic structured log records, different RNG seeds so `_large` is not a repeat of `_small`), `random_small.bin`/`random_large.bin` (`os.urandom`). Reuses `shannon_entropy` from `scripts/measure_entropy_periodicity.py` rather than reimplementing it.
- `data/corpus/SOURCES.md` — documents title, author, Gutenberg edition/URL, and public-domain justification (1813 publication, author died 1817).
- `data/corpus/baseline_entropy.csv` — entropy for all 6 files.
- **Git exception (one-time, narrow):** committed `data/corpus/*` only (`git add data/corpus`, commit `4f98ab8` "M3: freeze test corpus") and tagged `corpus-v1-frozen`, per explicit user decision to make a scoped exception for this milestone's freeze mechanism. Everything else in the repo remains untracked, exactly as before.

**Verified (baseline_entropy.csv):**

| file | size (bytes) | entropy (bits/byte) |
|---|---|---|
| text_small.txt | 10238 | 4.7268 |
| text_large.txt | 204799 | 4.6162 |
| json_small.json | 10313 | 4.5202 |
| json_large.json | 205012 | 4.5324 |
| random_small.bin | 10240 | 7.9804 |
| random_large.bin | 204800 | 7.9991 |

All 6 files within ±1% of their 10 KB/200 KB targets (well inside the ±10% requirement). Text/JSON land at 4.52–4.73 bits/byte (below the ~6.5 threshold), random at 7.98–8.00 (above the ~7.9 threshold) — the corpus genuinely spans the intended entropy range.

### M3 — Independent review: PASS (2026-08-18, first cycle, no retries)

Full checklist, commands, and design concerns in `docs/reviews/M3_review.md`. What the reviewer verified independently, not just re-stated from the implementer's report:

- Re-fetched the live Gutenberg source itself and confirmed the front-matter-skip logic lands exactly on the novel's real opening line, not merely on this run by luck.
- **Reproduced the corpus byte-for-byte** from a fresh download using the implementer's own slicing logic — strong evidence against silent tampering or a hand-edited substitute.
- Confirmed `json_large.json` is genuinely distinct from `json_small.json` (different seeds, zero duplicate records, no substring overlap) — ruled out a repeat-to-pad shortcut that would have hit the same size/entropy numbers with far less real variety.
- Independently recomputed entropy for all 6 files and matched `baseline_entropy.csv` to 6 decimal places.
- Confirmed via `git log --oneline --all` (exactly 2 commits total: M0 + M3) and `git status` that no scope creep occurred — only `data/corpus/*` was ever staged or committed, everything else remains untracked as before.
- Two non-blocking notes for later: `SOURCES.md`'s public-domain reasoning blends two different legal rules in one sentence (correct conclusion, worth tightening before reuse in the thesis text), and `build_corpus.py`'s live Gutenberg fetch isn't checksum-pinned (no risk to the already-frozen corpus, but a future rerun after Gutenberg revises its file would silently diverge rather than failing loudly).

**No required fixes. Verdict: PASS.**

**Follow-up (2026-08-18):** added `data/corpus/CHECKSUMS.sha256` (SHA-256 of
all 6 frozen files, generated after the `corpus-v1-frozen` tag) plus a
short pointer section in `SOURCES.md`, closing the review's
not-checksum-pinned note for the frozen corpus itself (the separate,
lower-priority note about pinning `build_corpus.py`'s live Gutenberg fetch
was left as-is). Committed under the same narrow git exception as the
rest of M3 (`git add project/data/corpus/CHECKSUMS.sha256
project/data/corpus/SOURCES.md`, commit `27982a4`) — confirmed via `git
status` that nothing outside `data/corpus/` was touched.

---

## M4 — Statistical Metrics Module

**Implemented:**
- `src/metrics.py` — `shannon_entropy` (numpy 256-bin histogram), `chi_square_uniform` (scipy against uniform 256-bin expectation), `compression_ratio` (gzip), `pearson_correlation` (numpy corrcoef). All four spot-checked directly by the reviewer on hand-picked inputs (random, constant-byte, corpus files, plaintext-vs-ciphertext pairs) — no mocking or hidden bugs found.
- `src/avalanche.py` — `avalanche_test(pipeline_encrypt_fn, data, n_trials=25)`: flips one random bit per trial, encrypts both copies, returns mean Hamming-distance percentage. Wrapped for each pipeline in `tests/test_avalanche.py`, extracting `post_classical["ciphertext"]` (excluding nonce/tag) as "the ciphertext."
- `tests/test_metrics.py` (15 tests) and `tests/test_avalanche.py` (2 tests) — both new.
- `scripts/check_avalanche_nonce_sensitivity.py` — ad hoc investigation script, now committed as a permanent, reusable reference (see below).

**Verified:** `pytest tests/test_metrics.py tests/test_avalanche.py -v` — 17/17 passed. Full suite: 37/37 (20 pre-existing + 17 new). Entropy sanity check matches `data/corpus/baseline_entropy.csv` to 5-6 decimal places (random ~7.98-7.99, text/JSON ~4.5-4.7). Avalanche percentages: Pipeline A 50.09%, Pipeline B 50.04% — both nominally within the 40-60% band required by the exit criteria.

### ⚠️ Central finding: `avalanche_test` does not actually measure avalanche/diffusion

Investigated empirically during implementation (not assumed either way), and independently reproduced by the reviewer **three separate ways**:
1. Bit-flip vs. no-flip-at-all — both land at ~50% (see `docs/test_raport.md`'s M4 section and `scripts/check_avalanche_nonce_sensitivity.py`).
2. Bit-flip vs. two entirely unrelated random inputs — also ~50%, same variance profile.
3. Confirmed in `src/classical_crypto.py`: every `encrypt_aes_gcm` call generates a fresh random nonce, with no override.

**Bit-flip, no-flip, and wholly-unrelated-input are statistically indistinguishable** through the full-pipeline AES-GCM ciphertext. The test is measuring AES-GCM's semantic-security property (fresh-nonce ciphertexts look random regardless of plaintext), not the pipeline's sensitivity to the specific input change — the same class of issue as M1's SHA-256 mask: a test that satisfies its own exit criteria for a reason unrelated to what it claims to measure.

**Why not just fix the nonce?** AES-GCM's core is CTR-mode keystream XOR. Under a *fixed* nonce, a single flipped plaintext bit produces, by construction, exactly one flipped ciphertext bit — "avalanche effect" (block-cipher-style diffusion) doesn't apply to stream-cipher-mode ciphertext the way M4's reference paper (a block-cipher study) assumes. Neither nonce policy makes full-pipeline AES-GCM output a meaningful avalanche measurement.

**Not resolved, deliberately carried forward:** `docs/milestone_plan.md`'s M6 task list specifies reusing `avalanche_test` with `n_trials=25` against this same full-pipeline signature. Doing so unchanged would let the thesis present a number meaning "AES-GCM is semantically secure" as if it meant "the DNA transform contributes properly to diffusion." **This needs an explicit decision before M6** — likely direction: measure avalanche on the DNA-transform's own pre-AES output for Pipeline A (a fixed-nonce-equivalent check found ~38%, high variance, but a real signal from the chained mod-4 design, unlike the current ~50% full-pipeline number).

### Follow-up (2026-08-23): DNA-transform-only avalanche measurement added

Closes the open question above with a real, well-powered measurement.
Reuses `avalanche_test` from `src/avalanche.py` completely unmodified —
only the wrapped "encrypt" function changes, now returning Pipeline A's
pre-AES `post_dna` bytes instead of the AES-GCM ciphertext body. Since
`dna_transform` is fully deterministic (no nonce), this isolates the
transform's own bit-flip diffusion from AES-GCM's nonce randomization.
Script: `scripts/measure_dna_transform_avalanche.py` (20 batches x 100
trials = 2,000 total flips per file, reported as mean/stdev/min/max
rather than a single noisy sample). New regression test:
`tests/test_avalanche.py::TestAvalanchePipelineADNATransformOnly` (25
trials, loose 0-100 sanity bound only — see below for why no 40-60%
assertion applies here). Full suite now 38/38 passing.

**Comparison: full-pipeline (meaningless) vs. DNA-transform-only (real signal)**

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

**What this shows:**
- The full-pipeline rows all land at ~50% no matter what — flipped, not flipped, or completely unrelated inputs — confirming that number carries no information; it's purely AES-GCM's per-call nonce randomization.
- The DNA-transform-only rows are a genuinely different, real signal: with the nonce removed entirely, one flipped input bit propagates to roughly **30-32%** of the transform's output bits, consistently across three very different data types (text, JSON, already-random bytes) — that cross-type consistency is itself informative about the chained mod-4 design.
- **Old (38.28%, 25 trials) vs. new (30-32%, 2,000 trials)** is why the earlier number wasn't citable: with only 25 trials the result swung from 3% to 70% run to run. 2,000 trials narrows the stdev to ~1.7-1.8% and shows the true mean is meaningfully lower than that one noisy sample suggested.
- ~30-32% is real but below the ~50% a textbook-ideal avalanche effect would show — substantial, non-trivial diffusion, clearly distinct from Pipeline B's "no DNA stage" result (~0.0012%), but not full-strength block-cipher-style diffusion. **This is the number to cite for the DNA transform's own avalanche behavior; the full-pipeline ~50% figures should not be presented as evidence of the transform's diffusion.**

Full script, methodology, and output: `docs/test_raport.md`'s M4 follow-up section.

### M4 — Independent review: PASS (2026-08-23, first cycle, no retries)

Full checklist, commands, and design concerns in `docs/reviews/M4_review.md`. Reviewer independently confirmed the finding above (not taken on the implementer's word), endorsed keeping the literal spec (random nonce) over a fixed-nonce alternative — both fail to give a meaningful number for a different reason — and flagged that M4's exit criteria as written are not adequate to validate the milestone's real objective, even though they're technically satisfied.

**No required fixes for M4 itself. Verdict: PASS.** Open item carried forward to before M6 (see above).

---

## M5 — Performance Benchmark Harness

**Implemented:**
- `src/benchmark.py` — `time_stage(fn, *args, n_reps=20)` (median/IQR/all-samples via `time.perf_counter()`, first run discarded as warm-up), `benchmark_pipeline(pipeline_fn, data, key, n_reps=20, reference_sequence=None)` (per-stage timings; the optional `reference_sequence` kwarg is a documented deviation, needed since the spec's literal 4-param signature can't invoke Pipeline A, which requires one), `throughput`, `size_overhead`.
- `tests/test_benchmark.py` (14 tests) and `scripts/run_benchmark_smoke.py` — both new.

**Verified:** `pytest tests/test_benchmark.py -v` — 14/14 passed. Full suite: 52/52 (38 pre-existing + 14 new). Smoke script confirmed non-zero timings/throughput for both pipelines across 3 independent runs (Pipeline A ~12.6-13.3ms total, Pipeline B ~0.0998-0.1001ms total — Pipeline B's `dna_transform_ms` is intentionally `0.0`, it has no DNA stage).

### ⚠️ Central finding: `size_overhead` is a structural no-op for real AES-GCM output

Independently verified by the reviewer, not just accepted from the implementer's own flagged caveat: `encrypt_aes_gcm` is CTR-mode keystream XOR with no block padding, so `len(ciphertext) == len(plaintext)` **always**, for any input size. `size_overhead()`, as exercised against the ciphertext body only, is therefore mathematically guaranteed to return **exactly 0.0%** for any real plaintext through either pipeline — not a coincidence of one run, a structural property of what bytes get passed to it. The one test that touches real pipeline output only asserted the result was *finite*, never checked *what* it was — so "14/14 passed" didn't surface this on its own, same pattern as M4's avalanche finding.

**Not resolved at review time, investigated properly before fixing anything (2026-08-23):** rather than assume nonce+tag should count, the actual cryptography convention was checked against real sources:
1. **Wikipedia, "Ciphertext expansion"** — defines expansion as the length increase from encryption, explicitly naming the case where the ciphertext "must include a message-unique Initialization Vector (IV)" as a standard cause — i.e. the nonce is conventionally counted when it travels with the ciphertext. https://en.wikipedia.org/wiki/Ciphertext_expansion
2. **Go standard library, `crypto/cipher` AEAD interface** — its `Overhead()` is documented as coming "typically... from authentication tags **and nonces**," with a worked example of 28 bytes (12-byte nonce + 16-byte tag) when the nonce is embedded in the transmitted output rather than derived out-of-band. https://pkg.go.dev/crypto/cipher

Since `src/pipeline.py`'s `post_classical` stage already bundles `{"nonce", "ciphertext", "tag"}` as one unit — the nonce is not handled out-of-band here — both sources confirm the nonce should count toward overhead, same as the tag. This isn't an arbitrary project choice; it matches how a real, precisely-specified AEAD interface defines this exact metric.

**Verified numerically** with `scripts/check_aead_overhead_convention.py` (does not modify `size_overhead()` itself — that function is a correct, generic calculator; only the bytes passed to it change):

```
1 byte                 | nonce=16B  tag=16B  ciphertext=1B      | body-only=0.0000%  full-AEAD=3200.0000%
16 bytes               | nonce=16B  tag=16B  ciphertext=16B     | body-only=0.0000%  full-AEAD= 200.0000%
100 bytes              | nonce=16B  tag=16B  ciphertext=100B    | body-only=0.0000%  full-AEAD=  32.0000%
10238 bytes (text_small) | nonce=16B  tag=16B  ciphertext=10238B | body-only=0.0000%  full-AEAD=   0.3126%
204800 bytes (text_large)| nonce=16B  tag=16B  ciphertext=204800B| body-only=0.0000%  full-AEAD=   0.0156%
```

Confirms pycryptodome's default GCM nonce is **16 bytes** (not the commonly-cited 12-byte/96-bit GCM standard — worth noting explicitly in the thesis, since a reader familiar with GCM might expect 12). "Full-AEAD" overhead is real, size-dependent, and substantial for small inputs (3200% at 1 byte) but nearly negligible at realistic corpus sizes (0.31% for `text_small.txt`, 0.016% for `text_large.txt`) — this is the number to cite for AES-GCM's actual on-wire cost; the flat 0.0000% "body-only" figure should not be used.

**Required change for M6, not yet applied to any code:** when M6's experiment script computes size overhead, pass `nonce + ciphertext + tag` (not `ciphertext` alone) as the "encrypted" argument to `size_overhead()`. The function itself needs no change.

### M5 — Independent review: PASS (2026-08-23, first cycle, no retries)

Full checklist, commands, and design concerns in `docs/reviews/M5_review.md`. Reviewer independently reproduced the ciphertext-body-always-zero finding by hand-testing `encrypt_aes_gcm` at 6 different sizes, confirmed the `reference_sequence` kwarg and Pipeline B's hardcoded `dna_transform_ms=0.0` are legitimate documented adaptations (not scope creep), and confirmed `time_stage`'s warm-up discard is real (verified in source and empirically). Also noted independently-measured per-stage timings don't sum exactly to `total_ms` (<5% discrepancy) — expected from separate median samples, not a defect, worth a footnote if M6 reports both side by side.

**No required fixes for M5 itself. Verdict: PASS.** Open item (size_overhead's input bytes) carried forward to before M6, now with the standard/convention behind the fix documented and verified rather than assumed.

---

## M6 — Full Experimental Run & Analysis

**The milestone the thesis's actual conclusions rest on.** Ran both pipelines against all 6 frozen corpus files for the first time using the real `data/aes_key.bin` and real `data/reference_sequence.txt` — everything before this used hand-built samples or ad hoc scripts.

**Implemented:**
- `scripts/run_experiment.py` — one official run, 129.67s, zero errors. Produced `results/experiment_results.csv`: 30 rows (6 files × 3 stages for Pipeline A + 6 files × 2 stages for Pipeline B), 18 columns, zero nulls/NaN.
- `scripts/make_figures.py` — `results/fig_entropy_by_stage.png`, `fig_avalanche_comparison.png`, `fig_compression_ratio_by_stage.png`, `table_throughput_size_overhead.csv`.
- `docs/findings.md` — 9 numbers-first bullets, every figure independently checked against the CSV to the last digit.
- **Both carried-forward decisions resolved and verified correct:** `avalanche_pct` computed per-row using each row's own stage output (input=trivial baseline, `post_dna`=real ~26-35% diffusion signal for Pipeline A, `post_classical`=the known ~50% nonce-driven figure for both pipelines — all three visible in one column via the existing `stage` column, no redundancy). `size_overhead_body_pct` (always ~0%, as expected) and `size_overhead_full_aead_pct` (real, size-dependent: ~0.31% small files, ~0.016% large files) computed as two separate columns every row.
- Reference paper (TIJER2604279.pdf) actually fetched and read in full (8 pages, via the plain `http://` URL after the `https://` version was repeatedly auto-rejected) — confirmed to contain no quotable DNA-LWCS numeric benchmarks, only qualitative claims; `docs/findings.md` documents this honestly rather than fabricating a comparison number.

**Verified:** Full suite still 52/52 passing (M6 touched no `src/`/`tests/` files). Corpus checksums still match `CHECKSUMS.sha256`. `git status` shows only new files under `scripts/`, `results/`, `docs/findings.md` — nothing under `data/corpus/` or `src/` touched.

### ⚠️ Central finding: the real entropy-class gap is smaller than M1's original narrative implied — corrected, not broken

Independently reproduced by the reviewer from raw data (not accepted from the implementer's report): running the real pipeline against the real corpus and real reference sequence gives a `post_dna` entropy gap of only **~0.05-0.10 bits/byte** (e.g. `text_small.txt`: 7.9265 vs. random's 7.9804) — much smaller than the ~0.6-0.7 bit gap implied by M1's section above (7.27-7.47 vs 7.95-7.96).

**Root-caused via four controlled swaps, not just noticed and left unexplained:** the M1-era measurements used a 64-nt reference sequence hardcoded as a literal in a script/test file — **never the actual frozen `data/reference_sequence.txt`** that every real pipeline call since M2 has used. Swapping the real corpus through the *old sample* reference reproduces a 0.22-bit gap (much closer to M1's claim); swapping M1's *old sample text* through the *real* reference reproduces something close to M6's small gap. The reference sequence, not the transform or the corpus, drives the difference.

**Why:** the real 61-nt reference is almost perfectly base-balanced (A:15/T:16/C:15/G:15) and contains five repeats of `AGCT` — a perfect period-4 cycle through all four mod-4 values under the default mapping — making it a far more effective "mixer" under the chained mod-4 design than the skewed, same-letter-run-heavy 64-nt sample literal (A:20 vs G:10) that M1's numbers were actually measured with.

**This is a real, reproducible, mechanistically-understood finding, not a bug** — and it should replace M1's originally-cited numbers everywhere in the thesis. See the correction note added directly to the M1 section above, and `docs/reviews/M6_review.md` for the full four-way isolation.

**Consolation/clarification:** entropy isn't actually the strongest surviving signal at `post_dna` anyway — chi-square and compression ratio show a proportionally much clearer separation (chi-square ~4.8-8.4x random's, vs. entropy's <1% relative gap), because entropy (a log-compressed summary) saturates near its maximum faster than chi-square (sensitive to higher-order deviations from uniformity) does. The thesis's core claim — that a measurable signal exists at `post_dna` and disappears by `post_classical` — still holds; only entropy's specific magnitude needed correcting.

**At `post_classical` (both pipelines):** the signal collapses toward random for all three metrics, as anticipated before this milestone started — AES-GCM makes ciphertext indistinguishable from random regardless of input structure. This is the direct, numbers-backed answer to the thesis's research question.

### M6 — Independent review: PASS (2026-08-23, first cycle, no retries)

Full checklist, commands, and design concerns in `docs/reviews/M6_review.md`. Beyond the central finding above, the reviewer independently: recomputed all headline entropy/chi-square/compression numbers from scratch and matched the CSV exactly; confirmed every one of `findings.md`'s 9 bullets against the CSV number-by-number with no rounding drift; independently re-fetched and read the TIJER paper to confirm the "no numeric benchmarks" claim wasn't a shortcut; viewed all 3 PNG figures directly and confirmed they render correctly; and independently re-verified corpus/repo integrity.

**One non-blocking recommendation:** `fig_entropy_by_stage.png`'s 0-8 y-axis visually flattens the ~0.05-0.10 gap that is this milestone's central finding — a skimming reader could easily miss it. **Recommended before thesis use:** a supplementary zoomed-in/delta-focused chart alongside the full-scale one.

**No required fixes for M6 itself. Verdict: PASS.**

## Next Milestone

**M7 — Thesis Writing.** M6 is done — `docs/findings.md` is finalized. Before drafting `03_methodology.md`/`05_results.md`/`06_discussion.md`, make sure to cite M6's entropy numbers, not M1's originally-claimed ones (see the correction note in the M1 section above), and consider addressing the entropy-chart rescale recommendation before embedding `fig_entropy_by_stage.png` in the thesis. See `docs/milestone_plan.md` for M7's full task list and exit criteria.