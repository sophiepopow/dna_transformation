# Thesis Milestone Plan

Analysis of the Impact of DNA Encoding on the Statistical Properties of
Lightweight Encryption — Minimum-Viable Scope (1-Month Execution)

Converted verbatim from `docs/dna_plan.pdf` (the original source document) on
2026-08-16, so that `CLAUDE.md` and the project's `.claude/agents/` /
`.claude/commands/run-milestone.md` — all of which name `docs/milestone_plan.md`
as the sole authoritative source of each milestone's tasks and exit criteria —
have an actual file to read. No content was changed in this conversion except
where explicitly marked as a later addendum (see the "M1 Revision" section).

**Research question:** Does a DNA-encoding transform produce a measurably
different statistical signature on low-entropy data (text/JSON) than on
high-entropy data (compressed/random), and does the effect disappear once
classical encryption is layered on top?

**Scope:** 3 data classes (text, JSON, random/compressed) × 2 sizes (~10 KB,
~200 KB) × 2 pipelines (DNA-transform + AES-GCM vs. AES-GCM only), measured at
3 pipeline stages (input, post-DNA-transform, post-classical-encryption).

**Deliberately out of scope:** full NIST SP 800-22 suite, ECC/ECDH key
exchange, DNA-sequence fitness function, RAM/CPU/energy profiling,
latency-for-small-messages as a separate study, multi-sequence/multi-mapping
comparisons.

| Milestone | Focus | Duration |
|---|---|---|
| M0 | Scope Lock & Environment Setup | Day 1 |
| M1 | DNA Encoding Layer | Days 2–3 |
| M2 | Classical Encryption Layer & Pipeline Composition | Day 4 |
| M3 | Test Corpus Construction | Day 5 |
| M4 | Statistical Metrics Module | Days 6–8 |
| M5 | Performance Benchmark Harness | Days 9–10 |
| M6 | Full Experimental Run & Analysis | Days 11–14 |
| M7 | Thesis Writing | Days 15–21+ |

**How to use this document:** each milestone below is written to be
executable by a coding agent (e.g. Claude Code) without further
clarification — tasks name exact file paths, function signatures, and
libraries; exit criteria are checkable pass/fail conditions. Complete
milestones strictly in order; do not begin a milestone until the previous
one's exit criteria all pass.

---

## M0 — Scope Lock & Environment Setup

Estimated duration: Day 1

**Objective:** Freeze the research question, in-scope/out-of-scope
boundaries, and development environment before any implementation begins.

**Reference paper:** *A Statistical Test Suite for Random and Pseudorandom
Number Generators for Cryptographic Applications* (NIST SP 800-22).
https://www.nist.gov/publications/statistical-test-suite-random-and-pseudorandom-number-generators-cryptographic
— Use for the scope-boundary caveat: statistical randomness testing is not a
substitute for formal cryptanalysis.

**Tasks (execute in order):**
1. Create project structure: `/project/src/`, `/project/data/corpus/`,
   `/project/results/`, `/project/docs/`, `/project/tests/`,
   `/project/scripts/`.
2. Write `docs/scope.md` containing the exact research question, the 3 data
   classes, the 2 pipelines, and the full out-of-scope list (NIST STS full
   suite, ECC/ECDH, DNA fitness function, RAM/CPU/energy profiling,
   small-message latency study).
3. Copy the scope-boundary sentence into `docs/scope.md`, adapted from NIST
   SP 800-22's statement that statistical testing cannot certify a generator
   as cryptographically secure and is not a substitute for cryptanalysis.
4. Set up the environment: `python -m venv .venv`; activate it; `pip install
   pycryptodome numpy scipy pandas matplotlib pytest`; freeze with `pip
   freeze > requirements.txt`.
5. Initialize git: `git init`; commit the empty project skeleton and
   `docs/scope.md` with message "M0: scope lock".

**Requirements:**
- Python 3.10 or newer available on the system.
- Sign-off (self or supervisor) on `docs/scope.md` before proceeding to M1 —
  treat this as a hard gate, not a formality.

**Exit criteria (must all pass before advancing):**
- `docs/scope.md` exists, is committed to git, and contains the research
  question verbatim, the 3 data classes, the 2 pipelines, and the
  out-of-scope list.
- `requirements.txt` exists and lists pycryptodome, numpy, scipy, pandas,
  matplotlib, pytest.
- Virtual environment activates with no errors; `python -c "import Crypto,
  numpy, scipy"` runs without ImportError.

> Note on task 2's parenthetical out-of-scope list (5 items) vs. the 6-item
> "Deliberately out of scope" list on the plan's overview page above (which
> additionally names "multi-sequence/multi-mapping comparisons"): the
> overview page is treated as the canonical full list — task 2 says to write
> "the full out-of-scope list," and the overview page is where that full list
> is actually enumerated. `docs/scope.md` should contain all 6 items.

---

## M1 — DNA Encoding Layer

Estimated duration: Days 2–3

**Objective:** Implement a reversible byte↔DNA mapping and a deterministic
DNA-derived transform (XOR mask + bit rotation), fully unit-tested for
round-trip correctness.

**Reference paper:** *DNA Encoded Elliptic Curve Cryptography System for IoT
Security*. https://arxiv.org/pdf/2311.11393 — Use for the standard
binary↔nucleotide mapping table (00=A, 01=T, 10=C, 11=G) and DNA
cryptography operation taxonomy.

**Tasks (execute in order):**
1. Create `src/dna_codec.py` with functions: `bytes_to_bits(data: bytes) ->
   str`, `bits_to_dna(bits: str, mapping: dict) -> str` using mapping
   `{"00":"A","01":"T","10":"C","11":"G"}`, `dna_to_bits(dna: str, mapping:
   dict) -> str`, `bits_to_bytes(bits: str) -> bytes`.
2. Create `data/reference_sequence.txt` containing a fixed 40–200 nucleotide
   reference DNA sequence (hardcoded string of A/T/C/G characters — no
   network fetch).
3. Create `src/dna_transform.py` with: `derive_mask(reference_sequence: str,
   length: int) -> bytes` (deterministically repeat/hash the reference
   sequence to the required byte length), `dna_transform(data: bytes, mask:
   bytes) -> bytes` (XOR with mask, then circular bit rotation by a fixed
   amount, e.g. 3 bits), and `dna_inverse_transform(data: bytes, mask:
   bytes) -> bytes` that exactly inverts it.
4. Write `tests/test_dna_codec.py`: generate 100 random byte strings of
   varying length (1 to 10,000 bytes) and assert `bits_to_bytes(bits_to_bits(x))
   == x` and `dna_to_bits(bits_to_dna(bits, m), m) == bits` for each.
5. Write `tests/test_dna_transform.py`: for the same 100 random byte
   strings, assert `dna_inverse_transform(dna_transform(x, mask), mask) ==
   x`.

**Requirements:**
- M0 complete and `docs/scope.md` approved.
- pytest installed in the active virtual environment.

**Exit criteria (must all pass before advancing):**
- Running `pytest tests/test_dna_codec.py tests/test_dna_transform.py -v`
  shows 100% pass rate with zero failures.
- Round-trip manually verified on one UTF-8 text sample and one binary
  sample (e.g. via a short Python REPL check), confirming byte-identical
  output.

### M1 Revision — addendum (added 2026-08-16, not in the original PDF)

The `derive_mask()` + XOR + fixed-rotation design specified above was
**implemented, passed every stated exit criterion above, and then replaced**
after an implementer subagent actually ran the pipeline and measured
entropy/autocorrelation directly (not something the exit criteria above
would have caught). Findings, in order of what was tried:

1. **SHA-256-based `derive_mask`, as specified.** Round-trip tests passed.
   Measured: text and JSON both converged to ~7.96 bits/byte after the
   transform — statistically indistinguishable from already-random data
   (~7.96 bits/byte). A cryptographically strong mask pushes *any* input
   toward near-maximal output entropy regardless of the input's original
   structure, which erases the exact entropy-class signal this thesis is
   designed to measure. This is a fatal design flaw for the research
   question, invisible to every exit criterion listed above.
2. **Tiled mask (reference sequence repeated, not hashed) + fixed rotation**,
   tried as a simpler intermediate fix. Round-trip tests passed. Measured:
   ciphertext-only autocorrelation at lag = reference-sequence-length-in-bytes
   was **0.835** on structured text (vs ~0.01 for random data) — a severe,
   trivially detectable periodicity artifact, structurally identical to a
   classic repeating-key XOR weakness.
3. **Chained mod-4 nucleotide addition (final design, currently
   implemented):** `c[i] = (plain[i] + ref[i mod len(ref)] + c[i-1]) mod 4`,
   no cryptographic primitive, no static mask, `c[-1] = 0` fixed IV. Each
   output nucleotide depends on the entire preceding stream, not just its
   position modulo the reference sequence's length. Measured: periodicity
   leak resolved (autocorrelation ~0.017, chance level), while a real
   entropy gap is preserved (text ~7.27–7.47, JSON ~7.46, random ~7.95–7.96
   bits/byte, independently re-measured — see
   `scripts/measure_entropy_periodicity.py` and `docs/test_raport.md`).

**This is a deviation from the literal task/exit-criteria text above**,
made because the literal spec's design is empirically unsound for this
thesis's research question, not because it failed its own stated tests —
it passed them. Per project workflow rules, deviations like this should be
surfaced rather than silently reconciled; this addendum is that surfacing.
Function signatures also changed as part of this: `dna_transform` /
`dna_inverse_transform` now take `reference_sequence: str` directly instead
of a precomputed `mask: bytes`, and `derive_mask` no longer exists in the
codebase.

If this project is revisited or extended, the exit criteria above ("100%
pass rate") should be read as necessary but not sufficient — see
`.claude/agents/milestone-reviewer.md` for why.

---

## M2 — Classical Encryption Layer & Pipeline Composition

Estimated duration: Day 4

**Objective:** Wire in AES-GCM as the classical cipher and compose the two
experimental pipelines, each capable of exposing intermediate stage outputs
for later measurement.

**Reference paper:** *Enhancing IoT security with a DNA-based lightweight
cryptography system*. https://www.nature.com/articles/s41598-025-96292-0 —
This is the DNA-LWCS source/baseline paper — use its 3-phase pipeline
structure and reported metrics as the comparison baseline in later analysis.

**Tasks (execute in order):**
1. Create `src/classical_crypto.py` using pycryptodome: `encrypt_aes_gcm(data:
   bytes, key: bytes) -> tuple[bytes, bytes, bytes]` (nonce, ciphertext, tag)
   via `AES.new(key, AES.MODE_GCM)`, and the matching
   `decrypt_aes_gcm(nonce, ciphertext, tag, key) -> bytes`.
2. Create `src/pipeline.py` with `pipeline_b_classical_only(data, key) ->
   dict` (AES-GCM only, returns stages `{"input":..., "post_classical":...}`)
   and `pipeline_a_dna_plus_classical(data, key, mask) -> dict` (DNA-transform
   then AES-GCM, returns stages `{"input":..., "post_dna":...,
   "post_classical":...}`).
3. Implement the matching decrypt functions `decrypt_pipeline_a` and
   `decrypt_pipeline_b` that exactly invert each pipeline.
4. Write `tests/test_pipeline.py`: for 20 random byte strings ranging from
   10 bytes to 200 KB, assert `decrypt_pipeline_a(pipeline_a_dna_plus_classical(x,
   key, mask)) == x` and the equivalent for pipeline B.

**Requirements:**
- M1 complete with all tests passing.
- pycryptodome installed; a fixed 16 or 32-byte AES key generated once and
  reused across all experiments (store in `data/aes_key.bin`, do not
  regenerate per run).

**Exit criteria (must all pass before advancing):**
- Running `pytest tests/test_pipeline.py -v` shows 100% pass rate.
- Both pipelines produce byte-identical round-trip decryption on all 20 test
  vectors.
- Pipeline A's return dict contains all 3 stage keys
  (input/post_dna/post_classical); Pipeline B's contains 2
  (input/post_classical).

> Note: Pipeline A's mask/reference-sequence parameter should be updated to
> match M1's actual final signature (`reference_sequence: str`, not
> `mask: bytes`) when M2 is implemented — see the M1 Revision addendum above.

---

## M3 — Test Corpus Construction

Estimated duration: Day 5

**Objective:** Build and permanently freeze a 3-class, 2-size test dataset
spanning the entropy spectrum from structured text to random binary.

**Reference paper:** *A New Look at the Classical Entropy of Written
English*. https://arxiv.org/pdf/0911.2284 — Use to justify the expected
entropy baseline for the text data class and to cite a real computed
English-text entropy figure instead of an assumed one.

**Tasks (execute in order):**
1. Create `scripts/build_corpus.py` that programmatically generates:
   `text_small.txt` (~10 KB) and `text_large.txt` (~200 KB) from a
   public-domain English text source (e.g. Project Gutenberg excerpt);
   `json_small.json` (~10 KB) and `json_large.json` (~200 KB) of synthetic
   structured config/log data; `random_small.bin` (~10 KB) and
   `random_large.bin` (~200 KB) via `os.urandom()`.
2. Write `data/corpus/SOURCES.md` documenting the exact text source (title,
   edition, URL) used for the text files, confirming public-domain status.
3. Compute Shannon entropy of each of the 6 files (reuse or stub the entropy
   function ahead of M4) and write results to
   `data/corpus/baseline_entropy.csv` with columns filename, size_bytes,
   entropy_bits_per_byte.
4. Add a comment at the top of `scripts/build_corpus.py`: "DO NOT MODIFY
   corpus after freezing — see git tag corpus-v1-frozen".
5. Commit the corpus and tag it: `git add data/corpus && git commit -m "M3:
   freeze test corpus" && git tag corpus-v1-frozen`.

**Requirements:**
- M0 complete.
- A confirmed public-domain text source (no copyrighted material) selected
  before writing files.

**Exit criteria (must all pass before advancing):**
- All 6 files exist under `data/corpus/`, each within ±10% of its target
  size.
- `baseline_entropy.csv` shows text and JSON files below ~6.5 bits/byte and
  random files above ~7.9 bits/byte, confirming the corpus spans the
  intended entropy range.
- Git tag `corpus-v1-frozen` exists and points at the commit containing the
  corpus.

---

## M4 — Statistical Metrics Module

Estimated duration: Days 6–8

**Objective:** Implement entropy, byte-distribution/chi-square,
compression-ratio, plaintext–ciphertext correlation, and avalanche-effect
metrics, each independently unit-tested.

**Reference paper:** *INRU: A Quasigroup Based Lightweight Block Cipher*.
https://arxiv.org/pdf/2112.07411 — Use as the direct methodological template
for the avalanche test: flip one bit per trial across many random inputs
and keys, then measure the Hamming-distance percentage between ciphertexts.

**Tasks (execute in order):**
1. Create `src/metrics.py` with: `shannon_entropy(data: bytes) -> float`
   (bits/byte via a 256-bin numpy histogram over byte values),
   `chi_square_uniform(data: bytes) -> float` (via `scipy.stats.chisquare`
   against a uniform 256-bin expectation), `compression_ratio(data: bytes)
   -> float` (`len(gzip.compress(data)) / len(data)`), and
   `pearson_correlation(a: bytes, b: bytes) -> float` (numpy corrcoef on
   byte arrays truncated to equal length).
2. Create `src/avalanche.py` with `avalanche_test(pipeline_encrypt_fn, data:
   bytes, n_trials: int = 25) -> float`: for each of n_trials, flip one
   random bit in a copy of data, run pipeline_encrypt_fn on both the
   original and the flipped copy, compute the Hamming distance between the
   two resulting ciphertexts divided by total ciphertext bits, and return
   the mean percentage across all trials.
3. Write `tests/test_metrics.py` asserting: `shannon_entropy(os.urandom(10000))
   > 7.9`; `shannon_entropy(b"a"*10000) < 0.1`; `compression_ratio(...)`
   returns a finite float on all corpus files; `compression_ratio` on
   highly repetitive data is below 0.5.
4. Write `tests/test_avalanche.py`: run `avalanche_test` on pipeline A and
   pipeline B using `text_small.txt`, assert the returned value is between 0
   and 100, and print it for manual sanity check (expected roughly 40–60%).

**Requirements:**
- M2 and M3 complete.
- numpy and scipy installed and importable.

**Exit criteria (must all pass before advancing):**
- Running `pytest tests/test_metrics.py tests/test_avalanche.py -v` shows
  100% pass rate.
- Manual sanity check confirms: random-file entropy > 7.9 bits/byte,
  text-file entropy meaningfully lower (roughly 4–5 bits/byte), and
  avalanche percentage for both pipelines falls within the 40–60% range.

---

## M5 — Performance Benchmark Harness

Estimated duration: Days 9–10

**Objective:** Build a reusable timing harness that measures per-stage
execution time, throughput, and ciphertext size overhead with repeated runs
and robust statistics.

**Reference paper:** *A Comprehensive Survey on the Implementations,
Attacks, and Countermeasures of the Current NIST Lightweight Cryptography
Standard (ASCON)*. https://arxiv.org/abs/2304.06222 — Use as the reference
metric set for lightweight-cipher performance reporting (throughput,
area/power/energy overhead) so your benchmark output is comparable to the
current NIST lightweight-crypto standard's evaluation style.

**Tasks (execute in order):**
1. Create `src/benchmark.py` with: `time_stage(fn, *args, n_reps: int = 20)
   -> dict` returning `{"median_ms":..., "iqr_ms":..., "all_samples":[...]}`,
   using `time.perf_counter()`, discarding the first run as warm-up.
2. Implement `benchmark_pipeline(pipeline_fn, data: bytes, key: bytes,
   n_reps: int = 20) -> dict` returning per-stage timings
   (`dna_transform_ms`, `classical_encrypt_ms`, `total_ms`).
3. Implement `throughput(data_size_bytes: int, total_ms: float) -> float`
   (bytes/sec) and `size_overhead(plaintext: bytes, ciphertext: bytes) ->
   float` (percentage increase in size).
4. Write `tests/test_benchmark.py`: run the harness on both pipelines with
   `text_small.txt`, assert all timing values are positive floats and
   throughput is finite.
5. Create `scripts/run_benchmark_smoke.py` that runs the harness once on
   `text_small.txt` for both pipelines and prints results to console.

**Requirements:**
- M2 and M3 complete.
- No hard requirement on machine load during timing, but note any known
  background load as a caveat in `docs/findings.md` later (M6) rather than
  blocking this milestone.

**Exit criteria (must all pass before advancing):**
- Running `pytest tests/test_benchmark.py -v` shows 100% pass rate.
- `scripts/run_benchmark_smoke.py` runs without error and prints non-zero
  timings and throughput values for both pipelines.

---

## M6 — Full Experimental Run & Analysis

Estimated duration: Days 11–14

**Objective:** Execute the complete metrics + benchmark matrix across the
frozen corpus, generate figures and tables, and write a numbers-first
findings summary.

**Reference paper:** *A Review of Lightweight Cryptography Techniques for
[IoT / DNA-LWCS]*. https://tijer.org/tijer/papers/TIJER2604279.pdf — Use its
reported DNA-LWCS baseline numbers (time, throughput, delay, energy) as an
external comparison point when interpreting your own throughput/size-overhead
results.

**Tasks (execute in order):**
1. Create `scripts/run_experiment.py` that, for each of the 6 corpus files ×
   2 pipelines: runs the pipeline capturing all stages (input/post_dna/
   post_classical for pipeline A; input/post_classical for pipeline B);
   computes all M4 metrics (entropy, chi-square, compression ratio,
   correlation vs. input) at each captured stage; computes all M5
   performance metrics; runs the M4 avalanche test with `n_trials=25`;
   appends one row per (file, pipeline, stage) to
   `results/experiment_results.csv`.
2. Run `scripts/run_experiment.py` exactly once end-to-end. Do not modify
   the corpus or any src/ file until the run completes and results are
   saved.
3. Create `scripts/make_figures.py` (matplotlib) generating from
   `results/experiment_results.csv`: `results/fig_entropy_by_stage.png`
   (grouped bar chart, one group per data class),
   `results/fig_avalanche_comparison.png` (pipeline A vs. B),
   `results/fig_compression_ratio_by_stage.png`, and
   `results/table_throughput_size_overhead.csv`.
4. Write `docs/findings.md`: 5–10 bullet points, each citing a specific
   number pulled directly from `experiment_results.csv`, stating whether the
   DNA-transform stage shows a measurable entropy/chi-square/compression
   shift on text and JSON versus the random file, and whether that shift is
   still visible after AES-GCM (pipeline A final stage) compared to pipeline
   B's output.

**Requirements:**
- M4 and M5 complete with all their tests passing.
- Corpus frozen — git tag `corpus-v1-frozen` exists and has not been
  altered.

**Exit criteria (must all pass before advancing):**
- `results/experiment_results.csv` contains one row per (file × pipeline ×
  stage) combination with no null or NaN values.
- All 4 figure/table files exist under `results/`.
- `docs/findings.md` contains at least one bullet point with a specific
  supporting number for each of the 3 data classes (text, JSON, random).

---

## M7 — Thesis Writing

Estimated duration: Days 15–21+

**Objective:** Draft and finalize the thesis document, ensuring every
numeric claim traces back to a validated result from M6.

**Reference paper:** *A systematic review of lightweight cryptographic
schemes for security and privacy in IoT*.
https://link.springer.com/article/10.1007/s10791-025-09755-3 — Use as the
primary related-work anchor — it names the same standard metric battery
(entropy, execution time, energy, throughput, NPCR/UACI) that this thesis
narrows down to, supporting your methodology choices as field-consistent.

**Tasks (execute in order):**
1. Create `docs/thesis/` with chapter files: `01_introduction.md`,
   `02_related_work.md`, `03_methodology.md`, `04_implementation.md`,
   `05_results.md`, `06_discussion.md`, `07_limitations.md`,
   `08_conclusion.md`.
2. `01_introduction.md`: state the governing thought and research question
   from `docs/scope.md` verbatim; introduce no claims beyond what
   `docs/findings.md` supports.
3. `02_related_work.md`: paraphrase (never quote verbatim beyond short
   attributed phrases) each paper referenced across milestones M0–M6, citing
   author/year/venue.
4. `03_methodology.md`: describe the 2-pipeline, 3-stage, 3-data-class
   design; include the NIST SP 800-22 scope-boundary sentence from
   `docs/scope.md` verbatim.
5. `04_implementation.md`: describe `src/dna_codec.py`, `src/dna_transform.py`,
   `src/classical_crypto.py`, and `src/pipeline.py` conceptually — no need to
   reproduce full source code inline.
6. `05_results.md`: insert all 4 figures/tables from `results/` with
   captions; state every number exactly as it appears in
   `experiment_results.csv` — do not round or restate it differently.
7. `06_discussion.md`: answer the research question directly, using only
   claims present in `docs/findings.md`.
8. `07_limitations.md`: list every item from `docs/scope.md`'s out-of-scope
   section as a deliberate, named limitation (not an oversight).
9. Concatenate all 8 chapter files, in order, into
   `docs/thesis/thesis_draft.md`.

**Requirements:**
- M6 complete; `docs/findings.md` finalized and not expected to change
  further.
- Full reading list from the related-work research phase available for
  citation.

**Exit criteria (must all pass before advancing):**
- `docs/thesis/thesis_draft.md` exists and contains all 8 chapters in the
  correct order.
- Every numeric claim appearing in the Results and Discussion chapters
  traces to a specific row in `results/experiment_results.csv` or a figure
  in `results/`.
- The Limitations chapter names every scope item cut from the original
  full-scope plan.
