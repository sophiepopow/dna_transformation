# M5 Review — Performance Benchmark Harness

Date: 2026-08-23
Reviewer: independent review subagent (milestone-reviewer methodology),
first cycle — no retries needed.

## Verdict: PASS

All literal exit criteria are met and independently reproduced. There is a
real design concern (below) structurally the same class of problem as the
M4 avalanche finding — a metric that is currently guaranteed to always
return exactly 0.0%, regardless of input, for the one usage pattern that
matters. Following this project's own M4 precedent (surfaced-but-unresolved
caveat, not an automatic FAIL), this is PASS with a required pre-M6
decision, not a retry-triggering defect.

## Exit criteria checklist

| Criterion | Command | Result |
|---|---|---|
| `pytest tests/test_benchmark.py -v` 100% pass | `/Users/sophiepopow/Documents/PK/master/dna/.venv/bin/python -m pytest tests/test_benchmark.py -v` | **14 passed** in 0.52s |
| Full suite unaffected | `pytest tests/ -v` | **52 passed** (38 pre-existing + 14 new) |
| `scripts/run_benchmark_smoke.py` runs without error, non-zero timings/throughput for both pipelines | Ran 3 independent times | All 3 completed with no errors. Pipeline A ~12.6-13.3ms total, ~770k-812k bytes/sec. Pipeline B ~0.0998-0.1001ms total, ~102.3-102.6M bytes/sec. Only Pipeline B's `dna_transform_ms` is zero, by design (no DNA stage) — not a defect |

## Verification of implementer's flagged deviations

- **`reference_sequence` kwarg** (added since `pipeline_a_dna_plus_classical` requires it and the spec's literal 4-param signature has no room): confirmed real, independent `time_stage` calls for `dna_transform`, `encrypt_aes_gcm`, and the full `pipeline_fn` — not derived by subtraction. Stage-sum vs. `total_ms` differed by 0.19-4.35% across 3 runs (expected noise from independently-sampled medians, not a decomposition of one call — worth a footnote if M6 reports both side by side).
- **Pipeline B's `dna_transform_ms = 0.0`** (vs. `None` in the separate `dna_transform_stats` field to distinguish "no stage" from "near-zero stage") — confirmed in source and live output, legitimate.
- **`time_stage`'s warm-up discard** — confirmed directly in source (`range(n_reps + 1)`, `samples_ms[1:]`) and empirically (`len(all_samples) == n_reps == 20`).
- **`throughput`/`size_overhead` arithmetic** — hand-tested directly on multiple inputs (including negative/zero-duration error cases and ciphertext-shrinkage), all correct.

No mocking, hardcoded results, or hidden bugs found anywhere in `src/benchmark.py`.

## Central finding: `size_overhead` is a structural no-op for real AES-GCM output

Independently verified, not just accepted from the implementer's flagged
caveat: `encrypt_aes_gcm` is CTR-mode keystream XOR with no block padding,
so `len(ciphertext) == len(plaintext)` **always**, for any input size
(hand-tested at 0, 1, 5, 100, 10238, and 204800 bytes). `size_overhead`,
as currently exercised against the ciphertext body only, is therefore
**mathematically guaranteed to return exactly 0.0%** for any real
plaintext through either pipeline — not a coincidence of this run, a
structural property of the metric's current wiring.

Meanwhile the excluded nonce (16 bytes) + tag (16 bytes) = 32 bytes fixed
overhead is genuine, size-dependent, and exactly the kind of number a
thesis "size overhead" section would want: **3200% for a 1-byte
plaintext, 32.0% for 100 bytes, 0.31% for text_small.txt (10238 bytes),
0.016% for a 200KB file.** This real effect is currently invisible to the
metric as wired.

Compounding this: the one test that touches real pipeline output
(`test_real_pipeline_ciphertext_overhead_is_finite`) only asserts
`math.isfinite(value)`, never *what* the value is — so "14/14 passed"
does not surface that the real-usage value is always exactly 0.0. This
required independent computation to discover, exactly as with M4's
avalanche finding.

**Required decision before M6:** compute `size_overhead` in the M6
experiment script against `len(nonce) + len(ciphertext) + len(tag)`
rather than the ciphertext body alone, so the metric reflects genuine
on-wire cost instead of a value fixed at 0.0% by construction. The
`size_overhead` function itself is generic and doesn't need to change —
only which bytes M6 passes to it.

## Design concerns (surface regardless of verdict)

1. **`size_overhead` no-op for real usage** — the headline concern, above. Needs an explicit pre-M6 decision, same as the M4 avalanche caveat.
2. **Independent per-stage timings don't sum exactly to `total_ms`** (<5% discrepancy observed) — not a defect, worth a one-line footnote in any M6 table reporting both.
3. **`reference_sequence` kwarg and Pipeline B's hardcoded `0.0`** — both legitimate, well-reasoned, clearly documented adaptations, verified against `src/pipeline.py`'s actual signatures. Not scope creep.

## Required fixes

None for M5 itself — verdict is PASS. The size_overhead question above is
a carry-forward decision for M6 planning, parallel to the M4 avalanche
caveat, not a retry-triggering defect.
