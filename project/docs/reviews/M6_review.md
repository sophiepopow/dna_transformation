# M6 Review — Full Experimental Run & Analysis

Date: 2026-08-23
Reviewer: independent review subagent (milestone-reviewer methodology),
first cycle — no retries needed.

## Verdict: PASS

This is the milestone the thesis's actual conclusions rest on, so every
check below was independently reproduced from raw data, not accepted from
the implementer's report — including, most importantly, re-running the
real pipeline against the real frozen corpus and the real reference
sequence to verify the headline numbers myself.

## Exit criteria checklist

| Criterion | Check | Result |
|---|---|---|
| `experiment_results.csv`: one row per (file × pipeline × stage), no nulls/NaN | Loaded directly with pandas | `shape=(30, 18)`, `isnull().sum().sum()==0`. Row structure confirmed: 6 files × 3 stages (A) + 6 files × 2 stages (B) = 30 |
| All 4 figure/table files exist under `results/` | `ls results/` + viewed all 3 PNGs directly | All present; correctly labeled, non-corrupted, sensible |
| `docs/findings.md`: ≥1 bullet per data class with a specific number | Checked all 9 bullets against the CSV, number by number | Every cited figure matches the CSV exactly, to the last displayed digit. Text/JSON/random each covered in ≥5 of 9 bullets |

Corpus/repo integrity independently confirmed: `shasum -a 256 -c
data/corpus/CHECKSUMS.sha256` → all 6 files OK; `git status` → only
`data/corpus/` tracked, as expected, nothing else touched. Full suite
independently re-run: `pytest tests/ -q` → 52 passed.

## Central finding — independently verified, root-caused, not a bug

**The real entropy-class gap on the actual frozen corpus is genuinely
smaller (~0.05-0.10 bits/byte at the `post_dna` stage) than the
~0.6-0.7 bits/byte figure `docs/raport.md`'s M1 section describes.**
Reproduced directly: ran `pipeline_a_dna_plus_classical` on the real
`data/aes_key.bin` + the real 61-nt `data/reference_sequence.txt` + all 6
real frozen corpus files, computed `shannon_entropy` on the real
`post_dna` output — numbers matched `experiment_results.csv` exactly
(e.g. `text_small.txt`: H=7.926545, chi²=1119.518, comp=0.983298,
identical to the CSV row).

**Root cause, isolated via four controlled swaps:**
- Real corpus + the M1-era 64-nt reference sequence (never actually wired
  into the codebase, only ever a literal in `scripts/measure_entropy_periodicity.py`/`tests/test_dna_transform.py`):
  gap **0.22** bits/byte — much bigger than the real 61-nt reference's 0.054.
- M1-era hand-built 4000-byte samples + the real 61-nt reference: intermediate (~0.09-0.32).
- M1-era samples + M1-era reference (reproducing the original raport numbers): H=7.474/7.351, matches raport.md's cited 7.27-7.47.
- Real corpus truncated to 4000 bytes + real reference (isolating sample-size alone): a smaller effect (~0.05 bit) than the reference-sequence swap (~0.17 bit).

**Mechanism:** the real, frozen `data/reference_sequence.txt` is almost
perfectly base-balanced (A:15/T:16/C:15/G:15 of 61 nt) and contains five
literal repeats of `AGCT`, which under the default 2-bit mapping is the
value sequence `[1,0,3,2]` — a perfect period-4 cycle through all four
mod-4 values. Under the chained mod-4 design, this acts as a near-ideal,
self-reinforcing mixer. The M1-era 64-nt literal, by contrast, is visibly
skewed (A:20 vs G:10) with same-letter runs — a much weaker mixer that
left more residual structure, producing M1's larger apparent gap.

**Conclusion: this is a real, reproducible, mechanistically-explained
methodological finding, not a bug.** `docs/raport.md`'s M1 section already
noted in passing that the real reference-sequence file "is not currently
read by any code," but the magnitude of that gap's consequence was never
previously quantified. Now that M2 onward actually wires the real file
into every pipeline run, the true entropy-class gap this thesis can
report is smaller than the project's own earlier narrative implied — and
that correction should be made explicitly in the thesis text, not left as
an implicit discrepancy between `docs/raport.md`'s M1 section and M6's
actual results.

**Secondary claim also verified independently:** chi-square and
compression ratio show a proportionally much clearer signal than entropy.
`text_small.txt` chi² is ~4.8x random's at `post_dna` (1119.5 vs 234.3);
`json_small.json` is ~8.4x (1960.0 vs 234.3) — both far more separated
than entropy's <1% relative gap. This has a legitimate statistical
explanation: entropy is a log-compressed summary that saturates near its
maximum quickly, while chi-square is sensitive to higher-order deviations
from uniformity that persist longer. Not a fluke.

## Design concerns (surface regardless of verdict)

1. **`fig_entropy_by_stage.png`'s 0-8 y-axis visually erases the exact
   signal `findings.md` calls "real but small."** At full scale, post_dna
   and post_classical bars for text/JSON look nearly identical height to
   a skimming reader, even though the ~0.05-0.10 gap is the central,
   hard-won finding of this milestone. **Recommended before thesis use:**
   a supplementary zoomed-in/delta-focused chart, so the figure doesn't
   visually undercut the exact point the prose is making.
2. **Both carried-forward decisions (avalanche_pct per-stage, dual
   size_overhead columns) confirmed implemented exactly as documented**,
   not simulated: `post_dna` avalanche 26.06-34.74% across the 6 files
   (consistent with the previously-established ~26-35% band);
   `post_classical` 49.96-50.04% for both pipelines.
   `size_overhead_full_aead_pct` non-zero only at `post_classical`,
   correctly size-dependent (~0.31% small files vs ~0.0156% large, ~20x
   ratio matching the fixed 32-byte nonce+tag overhead).
3. **Input-stage timing sentinel** (`0.0` for all four timing/throughput
   columns) confirmed implemented exactly as documented, the only
   reasonable way to avoid `benchmark.py`'s deliberate raise-on-zero-duration
   behavior — correctly presented as a sentinel, not a real rate.
4. **TIJER paper claim verified as accurate, not a shortcut.** Reviewer
   independently fetched and read the same 8-page PDF; the DNA-LWCS
   discussion (item 10, Aqeel et al. 2025) genuinely contains only the
   qualitative claim findings.md paraphrases, no numeric figure — the
   implementer did not fabricate or prematurely give up on a citation that
   was actually there.

## Required fixes

None — verdict is PASS. Recommendation 1 above (entropy chart rescale)
should be addressed before the figure goes into the thesis unchanged, but
is not a retry-triggering defect for M6 itself.
