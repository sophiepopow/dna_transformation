# Reference-Sequence Factorial Experiment — Results Report

Date: 2026-09-06
Scope: follow-up to thesis Section 7.4 (`docs/thesis_skeleton_en.tex`), which
found that the measured `post_dna` entropy gap depends heavily on which
reference sequence is used, but only ever compared two sequences that
differed on two axes at once (base balance and mask period). This task
crosses those two factors in a 2x2 design to separate their effects, plus
independently verifies two analytic claims the thesis makes about the
transform's mechanics.

**Status: scripts are written and have been run; their output is real.
The scripts are `git add`-staged but NOT committed — no commit hash exists
yet.** Everything below is the actual output of running the committed-pending
scripts, not fabricated or estimated.

---

## Background

The transform's recurrence is a running (prefix) sum mod 4:

```
c_i = (p_i + r_{i mod L} + c_{i-1}) mod 4,   c_{-1} = 0
```

Two previously-confounded candidate explanations for why the real
61-nt reference sequence produces a smaller entropy gap than an old
64-nt sample sequence:

- **Candidate 1 (base balance):** a reference disproportionately one
  base (value 0 under A=0/T=1/C=2/G=3) contributes near-nothing at many
  positions, weakening the mixer.
- **Candidate 2 (mask period):** since `R_{i+L} = (R_i + S) mod 4` where
  `S = sum(r) mod 4`, the accumulated mask repeats with period L when
  `S ≡ 0`, and a longer period (2L or 4L) otherwise. `S ≡ 0` reproduces
  the exact periodicity the feedback term was introduced to remove
  (Section 6.2's tiled-mask design, rejected for a lag-L autocorrelation
  of 0.835).

Four cells, all L=61 nucleotides (matching the real reference), solved
so balance and S mod 4 vary independently:

| cell | composition | balance | S | S mod 4 |
|---|---|---|---|---|
| **A** (= real sequence's cell) | A15 T16 C15 G15 | balanced | 91 | 3 |
| **B** | A15 T15 C16 G15 | balanced | 92 | 0 |
| **C** | A20 T16 C16 G9 | skewed (A:G ≈ 2.2) | 75 | 3 |
| **D** | A20 T15 C17 G9 | skewed (A:G ≈ 2.2) | 76 | 0 |

---

## Deliverable 1: Scripts

All under `project/scripts/`, staged but not committed:

- **`measure_reference_sequence_factorial.py`** — generates 20 random
  permutations per cell (fixed, recorded seeds) plus one extra case
  using the real reference sequence in its real order (`A_real`), runs
  `dna_transform` (DNA stage only, no AES-GCM, no key) over the three
  small frozen corpus files, and writes
  `results/reference_sequence_factorial.csv`.
- **`summarize_reference_sequence_factorial.py`** — computes per-cell
  mean/sd, two-sample t-statistics isolating the balance effect and the
  S-mod-4 effect, and a z-score for the real sequence against its own
  cell's permutation distribution.
- **`verify_prefix_sum_and_avalanche_closed_form.py`** — Task 2: prefix-sum
  equivalence check (1000+ random inputs) and avalanche closed-form
  verification (2,000-trial re-run + direct mechanism check + factor
  decomposition).
- **`measure_avalanche_by_flip_position.py`** — Task 3: avalanche measured
  with the flip position constrained to 1/10/25/50/75/90/99% of the input.

All four reuse `src/dna_transform.py`, `src/dna_codec.py`,
`src/metrics.py`, and `src/avalanche.py` unmodified — no reimplementation
of entropy, chi-square, the transform, or the avalanche Hamming-distance
logic. Nothing under `data/corpus/`, `data/reference_sequence.txt`, or
`src/` was modified.

Checksums (`data/corpus/CHECKSUMS.sha256`) were verified against the live
corpus files before any measurement ran.

---

## Deliverable 2: `results/reference_sequence_factorial.csv`

243 rows: 81 reference sequences (4 cells x 20 permutations + 1 real-order
case) x 3 corpus files. Columns:

```
reference_id, cell, composition, balance, s_mod_4, permutation_seed,
data_class, file, entropy_post_dna, chisq_post_dna, autocorr_lag_L,
entropy_gap_text, entropy_gap_json
```

Sample rows:

```csv
reference_id,cell,composition,balance,s_mod_4,permutation_seed,data_class,file,entropy_post_dna,chisq_post_dna,autocorr_lag_L,entropy_gap_text,entropy_gap_json
A_0,A,A15T16C15G15,balanced,3,1000,text,text_small.txt,7.962831598677258,509.3991013869897,0.005767684851835946,0.017149801298283585,0.024761865148209772
A_0,A,A15T16C15G15,balanced,3,1000,json,json_small.json,7.955219534827332,643.1198487346068,0.00023158648692108281,0.017149801298283585,0.024761865148209772
A_0,A,A15T16C15G15,balanced,3,1000,random,random_small.bin,7.979981399975542,282.45000000000005,-0.0006284569031923352,0.017149801298283585,0.024761865148209772
C_0,C,A20T16C16G9,skewed,3,3000,text,text_small.txt,7.939090691768288,849.5155303770268,-0.007925677638112782,0.04399818686914525,0.05265634718112899
C_0,C,A20T16C16G9,skewed,3,3000,json,json_small.json,7.9304325314563044,997.8907204499175,-0.0017896755014186216,0.04399818686914525,0.05265634718112899
C_0,C,A20T16C16G9,skewed,3,3000,random,random_small.bin,7.983088878637433,239.35,0.003944866781061922,0.04399818686914525,0.05265634718112899
A_real,A,A15T16C15G15,balanced,3,,text,text_small.txt,7.9265450817616605,1119.5182652861888,-0.006909727701016213,0.056869583893272235,0.10484473705240038
A_real,A,A15T16C15G15,balanced,3,,json,json_small.json,7.878569928602532,1960.0317075535734,-0.0014830338254851693,0.056869583893272235,0.10484473705240038
A_real,A,A15T16C15G15,balanced,3,,random,random_small.bin,7.983414665654933,234.25,0.0028137939365737025,0.056869583893272235,0.10484473705240038
```

(The full 243-row file is at `results/reference_sequence_factorial.csv`.)

---

## Deliverable 3: Summary table

Mean ± sd across the 20 permutations per cell, text data class:

| cell | balance | S mod 4 | entropy gap (text) | chi-sq text post_dna | autocorr lag-L (text) |
|---|---|---|---|---|---|
| A | balanced | 3 | 0.0188 ± 0.0053 | 513.1 ± 77.2 | −0.0026 ± 0.0030 |
| B | balanced | 0 | 0.0196 ± 0.0059 | 531.8 ± 70.1 | +0.0002 ± 0.0045 |
| C | skewed | 3 | 0.0383 ± 0.0069 | 791.3 ± 86.1 | −0.0027 ± 0.0038 |
| D | skewed | 0 | 0.0361 ± 0.0052 | 762.8 ± 74.2 | +0.0023 ± 0.0041 |

**A_real** (real sequence, real order, n=1, not part of the 20-permutation
averages): entropy gap = **0.0569**, chi-sq = **1119.52**, autocorr =
**−0.0069**.

JSON data class, entropy_gap_json, for completeness:

| cell | mean | sd |
|---|---|---|
| A | 0.0324 | 0.0084 |
| B | 0.0345 | 0.0102 |
| C | 0.0568 | 0.0126 |
| D | 0.0520 | 0.0086 |

Two-sample t-statistics (isolating each factor, holding the other fixed;
`se` = standard error of the difference, combining both groups' sample
variances over n=20 each):

| comparison | metric | diff | se | t |
|---|---|---|---|---|
| C vs A (skewed vs balanced, S=3) | entropy gap | +0.0195 | 0.0019 | **10.05** |
| D vs B (skewed vs balanced, S=0) | entropy gap | +0.0164 | 0.0018 | **9.38** |
| A vs B (S=3 vs S=0, balanced) | entropy gap | −0.0008 | 0.0018 | −0.46 |
| C vs D (S=3 vs S=0, skewed) | entropy gap | +0.0022 | 0.0019 | 1.17 |
| A vs B (S=3 vs S=0, balanced) | autocorr lag-L | −0.0029 | 0.0012 | −2.39 |
| C vs D (S=3 vs S=0, skewed) | autocorr lag-L | −0.0051 | 0.0013 | **−4.03** |

Real sequence vs. its own cell's (A's) 20-permutation distribution
(z-score = (real value − permutation mean) / permutation sd):

| metric | A_real | cell-A perm mean ± sd | z |
|---|---|---|---|
| entropy_gap_text | 0.0569 | 0.0188 ± 0.0053 | **7.21** |
| chisq_post_dna (text) | 1119.52 | 513.08 ± 77.18 | **7.86** |
| autocorr_lag_L (text) | −0.0069 | −0.0026 ± 0.0030 | −1.43 |

---

## Deliverable 4: Verdict on P1 / P2 / P3

**P2 (balance dominates) holds, cleanly.** Balance is a large, highly
significant effect on the entropy gap (t ≈ 9–10 in both S-controlled
comparisons) and is roughly flat across S mod 4 (t ≈ −0.5 to 1.2, not
significant). Skewed reference sequences leave roughly double the
residual entropy gap of balanced ones, regardless of S.

**P1 (mask period dominates) does NOT hold as stated.** There is no
"markedly larger" autocorrelation for S≡0 approaching 0.835 — all four
cells sit within about ±0.005 of chance level (essentially zero). There
is a small, statistically detectable directional effect (S≡0 slightly
higher autocorrelation than S≡3, significant for the skewed pair at
t=−4.03) but it is two to three orders of magnitude too small to
constitute a practical periodicity leak. **This is a genuine null result**
for "S mod 4 alone causes a detectable lag-L leak" at this L — it should
be reported as such, not tuned away or omitted.

**P3 (both matter as separate main effects):** only half true. Balance is
real and dominant; S mod 4 has a real but practically negligible effect.
Not a symmetric 2x2 story — one factor clearly drives the result.

**Unplanned but important finding, not one of the stated predictions:**
the real reference sequence, in its real specific order, is a striking
outlier even against random reshuffles of its *own* composition — about
7–8 standard deviations *worse* (bigger entropy gap, higher chi-square)
than the average random permutation of the same multiset in cell A. A
typical random shuffle of the real sequence's own composition mixes
*better* than the real sequence's actual order does. **This directly
contradicts the thesis's current §7.4 explanation**, which credits the
`AGCT`-repeat pattern with making the real sequence "a more effective
mixer" — the data says the opposite: whatever the real sequence's
specific order is doing, it is measurably worse than an average random
order of the same composition, not better. §7.4 needs to be corrected to
reflect this (currently it says the AGCT-repeat is "coincidental, not
causally load-bearing" — that phrasing undersells it: the data now says
the real order actively underperforms a random baseline, which is a
stronger and different claim than "coincidental").

---

## Deliverable 5: Task 2 results

### Claim 1 — prefix-sum equivalence: **PASS**

`dna_transform(data, ref)`'s output nucleotide sequence was checked
against an independently computed running sum
`cumsum(p_j + r_{j mod L}) mod 4` for 1000 cases (random lengths 0–5000
bytes, including explicit length-0 and length-1 cases, fixed seed
20260906). All 1000 matched exactly.

### Claim 2a — 2,000-trial avalanche re-run

Two independent (unseeded — `avalanche_test` has no fixed RNG seed) runs:

| file | run 1 | run 2 |
|---|---|---|
| text_small.txt | 31.28% (sd 2.23%*) | 31.90% (sd 1.97%) |
| json_small.json | 31.12% (sd 1.71%) | 30.76% (sd 1.72%) |
| random_small.bin | 31.29% (sd 1.78%) | 31.83% (sd 2.67%) |

*sd here is across the 20 batch-means, not across all 2000 individual trials.

Both runs land in the same 30.4–31.9% band, consistent with the thesis's
"30-32%" claim. My pass threshold (30.4–31.8%, taken from one specific
historical run in `docs/test_raport.md`) is too strict given
`avalanche_test` has no fixed seed — run 2's text (31.90%) and random
(31.83%) fall just outside it. **This is ordinary sampling variation, not
a failure of the underlying claim.**

### Claim 2b — mechanism check: **PASS (0/500 violations)**, after one bug fix

For 500 single-bit-flip trials on `text_small.txt`, verified that every
output nucleotide before the flip position is byte-identical between
original and flipped `post_dna` output, and every nucleotide from the
flip position onward is shifted by the exact same nonzero constant mod 4.

**Bug encountered and fixed during verification:** the first attempt
reported 500/500 violations. Root cause: `avalanche_test`'s bit indexing
(`1 << bit_in_byte`, bit_in_byte=0 = LSB) is mirrored relative to
`dna_codec.bytes_to_bits`'s bit-string convention (`f"{b:08b}"`,
MSB-first), so the flipped-nucleotide index computed from the raw
`bit_index` was off. Fixed by converting to the MSB-first string position
(`byte_index*8 + (7 - bit_in_byte)`) before dividing by 2. After the fix,
0/500 violations. This is flagged explicitly per the task's
"report a number you cannot reproduce" instruction — the aggregate
statistics (downstream fraction, bit-diff fraction) happened to look
correct even with the bug, because they average over many random
positions; only the exact per-trial mechanism check was sensitive to it.

### Claim 2c — factor decomposition

| quantity | measured | theory |
|---|---|---|
| downstream fraction (mean) | 0.4955 | ~0.5 |
| downstream-only bit-diff fraction (mean) | 62.19% | ~62.5% |
| product | 30.81% | 31.25% |
| overall avalanche (same 500-trial set) | 30.62% | — |

The closed form `0.5 x 62.5% = 31.25%` holds to within measurement noise,
confirmed via both factors independently, not just the final product.

---

## Deliverable 5b: Task 3 (optional, completed) — avalanche by flip position

300 trials per position, `text_small.txt`. "Flip position at X%" =
flipped bit chosen uniformly among the 8 bits of the byte at index
`round(X% * len(data))`.

| flip position | mean avalanche | stdev |
|---|---|---|
| 1% | 61.59% | 12.52% |
| 10% | 56.54% | 11.26% |
| 25% | 46.09% | 9.27% |
| 50% | 31.70% | 6.24% |
| 75% | 15.78% | 3.15% |
| 90% | 6.31% | 1.24% |
| 99% | 0.62% | 0.13% |

Near-linear decline as predicted. The ceiling near 62% (not 100%) at the
1% position matches the 62.5% per-nucleotide bit-diff factor from Claim
2c exactly. The 50% point (31.70%) lands almost exactly on the whole-file
average (30-32%), as expected since a uniformly random flip position
averages to ~50% downstream. Saved to
`results/avalanche_by_flip_position.csv`.

---

## Deliverable 6: Environment

| | |
|---|---|
| Python | 3.11.7 |
| PyCryptodome | 3.23.0 |
| NumPy | 2.4.6 |
| SciPy | 1.17.1 |
| OS | macOS, Darwin 23.2.0, arm64 |
| CPU | Apple M2 |

Matches the expected values stated in the task spec exactly.

**Git/reproducibility caveat:** `project/src/`, `project/scripts/`,
`project/results/`, and `thesis_skeleton_en.tex` are all untracked in
this repo except for early M0/M3 milestone commits (scope lock, corpus
freeze). The four new scripts are currently `git add`-staged but **not
committed** (the commit was interrupted) — no commit hash exists for this
work yet. There is also no configured git remote.

---

## Deliverable 7: Deviations from spec

1. **Autocorrelation metric changed from the M1-era script's definition.**
   The task asked to reuse the M1-era script's exact autocorrelation
   definition if it still exists, for comparability with Section 6.2's
   0.835/−0.008/0.017 figures. It does exist
   (`scripts/measure_entropy_periodicity.py`), but its actual metric is a
   **byte-level XOR-preservation ratio** at `period_bytes = L/4` — not a
   Pearson correlation — and it requires L divisible by 4. All four cells
   here use L=61 (not divisible by 4; 61/4 = 15.25), so that definition
   cannot be reused unmodified without picking an arbitrary, wrong lag.
   **Resolution:** used the task's own fallback (Pearson correlation
   between `nt[:-L]` and `nt[L:]` on the nucleotide-value sequence),
   reusing `src/metrics.py`'s `pearson_correlation()` unmodified. Reported
   here as `autocorr_lag_L`. **These numbers are not directly numerically
   comparable to Section 6.2's 0.835/0.017 figures** — different metric,
   different lag granularity (nucleotide vs. byte). They are only
   qualitatively comparable (near 0 = no leak, large magnitude = leak).

2. **Commit not completed.** Deliverable 1 asked for "the script(s),
   committed, with the commit hash." The commit was interrupted before
   completion. The four scripts are staged (`git add`) but not committed;
   no hash exists. Whoever picks this up should either complete the
   commit or decide differently.

3. Everything else ran exactly as specified: all four cells' compositions
   and S mod 4 values verified against the spec table before running;
   corpus checksums verified before reading; no files under `data/corpus/`,
   `data/reference_sequence.txt`, or `src/` were modified; all statistical
   functions were imported from `src/metrics.py`/`src/avalanche.py`, not
   reimplemented.
