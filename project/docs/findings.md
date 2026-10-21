# M6 Findings — Full Experimental Run & Analysis

Source data: `results/experiment_results.csv` (30 rows: 6 corpus files x 2
pipelines x their captured stages, one clean run, see
`scripts/run_experiment.py`). Every number below is pulled directly from
that file — no rounding beyond what's shown, no restating.

- **Entropy: a real but small DNA-transform shift on text/JSON, not a
  large one.** `text_small.txt` entropy rises from **4.726758** bits/byte
  (input) to **7.926545** bits/byte (Pipeline A, post_dna) — closer to,
  but still measurably below, `random_small.bin`'s own baseline entropy
  of **7.980441** bits/byte (input stage) — a residual gap of **0.0539
  bits/byte**. `json_small.json` shows a larger residual gap: input
  **4.520237** -> post_dna **7.878570**, vs. random's 7.980441 (gap
  **0.1019** bits/byte). The same pattern holds at the larger size:
  `text_large.txt` post_dna is **7.939170** vs. `random_large.bin`'s own
  input entropy of **7.999148** (gap 0.0600); `json_large.json` post_dna
  is **7.910146** (gap 0.0890). Random itself barely moves through the
  transform (`random_small.bin`: 7.980441 -> 7.983415), as expected for
  already-near-maximal-entropy input.

- **Chi-square is the sharpest surviving signal.** `text_small.txt`'s
  chi-square statistic drops from **139108.219** (input) to **1119.518**
  (Pipeline A, post_dna) — still nearly **5x** `random_small.bin`'s own
  post_dna chi-square of **234.250**, meaning the DNA transform leaves a
  clearly measurable non-uniformity behind that entropy alone understates.
  `json_small.json` shows an even larger residual: input **179852.453**
  -> post_dna **1960.032**, roughly **8.4x** random's post_dna value.

- **Compression ratio tells the same story, most dramatically for
  JSON.** `text_small.txt` compression ratio goes from **0.430064**
  (input, compresses well) to **0.983298** (Pipeline A, post_dna) —
  nearly as incompressible as `random_small.bin`'s own post_dna ratio of
  **1.002246**. `json_small.json` retains more compressibility after the
  transform than text does: input **0.181712** -> post_dna
  **0.845923** — still visibly below random's ~1.0022, unlike text's
  near-complete convergence.

- **The shift is fully erased by AES-GCM (Pipeline A's final stage),
  matching Pipeline B's output.** At `post_classical`, `text_small.txt`
  under Pipeline A reads entropy **7.980532** / chi-square **273.103** —
  statistically indistinguishable from Pipeline B's (no DNA stage at all)
  entropy **7.981691** / chi-square **260.250** on the identical file,
  and both are close to `random_small.bin`'s own post_classical figures
  (Pipeline A: 7.982730 / 242.300; Pipeline B: 7.983776 / 229.050). The
  same holds for JSON (Pipeline A post_classical: 7.981366 / 267.597;
  Pipeline B: 7.982769 / 247.689). **Whatever entropy/chi-square/
  compression signal survives the DNA transform alone (bullets above) is
  gone by the time AES-GCM has run** — the two pipelines' final
  ciphertexts are not meaningfully distinguishable on these metrics for
  any of the 3 data classes.

- **Avalanche: the real diffusion signal lives only at post_dna, not
  post_classical.** Per the carried-forward M4 decision (see
  `scripts/run_experiment.py`'s docstring and `docs/raport.md`'s M4
  section), avalanche is measured on each row's own stage output.
  Pipeline A's post_dna avalanche (no AES-GCM nonce involved, this run's
  25-trial sample) is **34.739%** for `text_small.txt`, **30.810%** for
  `json_small.json`, and **26.060%** for `random_small.bin` — a real,
  substantial, data-class-consistent diffusion effect (the project's
  higher-powered 2000-trial measurement in
  `scripts/measure_dna_transform_avalanche.py` narrows these to a stable
  ~30-32% band; this run's 25-trial numbers are noisier single samples of
  the same underlying effect, as `docs/raport.md` already documents). At
  `post_classical`, every file on both pipelines lands at ~50% regardless
  of data class (Pipeline A: 50.035% text / 50.004% json / 50.039%
  random; Pipeline B: 50.023% / 50.011% / 49.962%) — confirming this
  number reflects AES-GCM's per-call random nonce, not the DNA
  transform's diffusion, and must not be cited as evidence of the
  transform's own behavior.

- **Correlation vs. input collapses immediately at post_dna, for all
  three classes.** Pearson correlation between the original input and
  Pipeline A's post_dna bytes is **-0.002392** (text_small), **-0.006998**
  (json_small), and **-0.005140** (random_small) — all near zero,
  confirming the chained mod-4 transform destroys linear correlation with
  the plaintext regardless of the input's original structure, before
  AES-GCM is even applied.

- **Throughput: Pipeline B is roughly two orders of magnitude faster.**
  On `text_small.txt`, Pipeline A's end-to-end throughput (post_classical
  stage) is **805,095.74 bytes/sec** vs. Pipeline B's **102,572,319.69
  bytes/sec** — Pipeline B is ~127x faster. The gap holds at the larger
  size: `text_large.txt` Pipeline A is **787,771.97 bytes/sec** vs.
  Pipeline B's **135,437,921.16 bytes/sec** (~172x faster). Same pattern
  for JSON (`json_small.json`: 788,367.75 vs. 99,522,312.92 bytes/sec) and
  random (`random_small.bin`: 769,957.40 vs. 102,399,488.50 bytes/sec) —
  the DNA-transform stage, implemented as a pure-Python per-nucleotide
  loop, is the dominant cost of Pipeline A by a wide margin.

- **Size overhead: the body-only convention is exactly 0% everywhere;
  the real overhead only appears once nonce+tag are counted.** Per the
  carried-forward M5 decision, `size_overhead_body_pct` is **0.0%** for
  all 30 rows without exception (`results/table_throughput_size_overhead.csv`
  confirms this column is uniformly 0.0), reproducing `docs/raport.md`'s
  M5 finding that AES-GCM's ciphertext body never grows relative to
  plaintext. `size_overhead_full_aead_pct` (nonce+ciphertext+tag vs.
  input) is the real, size-dependent number: **0.312561%** for
  `text_small.txt` (10238 bytes) but only **0.015625%** for
  `text_large.txt` (204799 bytes) — the fixed 32-byte (16-byte nonce +
  16-byte tag) overhead matters proportionally far more for small
  messages. Consistent across all 3 data classes: `json_small.json`
  0.310288% vs. `json_large.json` 0.015609%; `random_small.bin` 0.3125%
  vs. `random_large.bin` 0.015625%.

- **External DNA-LWCS comparison — paper fetched and read successfully,
  but it reports no quantitative DNA-LWCS numbers to compare against.**
  M6's reference paper, *A Review of Lightweight Cryptography Techniques
  for Securing IoT Networks* (TIJER, Vol. 13 Issue 4, April 2026,
  `http://tijer.org/tijer/papers/TIJER2604279.pdf` — the `https://` URL
  failed in this environment; plain `http://` succeeded), was fetched in
  full (8 pages) and read directly. Its DNA-LWCS discussion (Section 3,
  item 10, citing Sehrish Aqeel et al. 2025, *Enhancing IoT Security with
  a DNA-Based Lightweight Cryptography System* — the same paper named
  back in M2's spec) confirms the three-phase structure already assumed
  in this project (DNA-sequence-derived key generation, then
  substitution/transposition encoding, then ECC encryption) but reports
  **only qualitative performance claims, no numbers**: "DNA-LWCS is
  faster at encryption and has a stable throughput -- but the energy
  consumption is moderate when compared to other methods" (direct
  paraphrase of the review's own wording; the review itself does not
  quote a single ms/MB-s/mJ figure for DNA-LWCS, unlike some of its other
  reviewed papers, e.g. it does quote ASCON-128a's throughput as 2.42
  MB/s on an ESP32 and 124 MB/s on a Raspberry Pi 4, and BLEND's
  transmission delay as 65-110 microseconds per packet). **So this
  project's own measured numbers above (Pipeline A ~770-815 Kbytes/sec,
  Pipeline B ~99.5-135.9 Mbytes/sec) cannot be directly benchmarked
  against a DNA-LWCS figure, because the cited review paper does not
  publish one** -- only the qualitative direction ("DNA-LWCS is faster
  than other methods it's compared against, with moderate energy cost")
  is available from this source, and no number is fabricated here to
  fill that gap.
