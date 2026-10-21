"""
scripts/run_experiment.py

M6: Full Experimental Run. For each of the 6 frozen corpus files x 2
pipelines x captured stage, runs the pipeline, computes all M4 statistical
metrics, all M5 performance metrics, and the M4 avalanche test, then
appends one row to results/experiment_results.csv.

Reuses, unmodified: src/pipeline.py (pipeline_a_dna_plus_classical,
pipeline_b_classical_only), src/metrics.py (shannon_entropy,
chi_square_uniform, compression_ratio, pearson_correlation),
src/avalanche.py (avalanche_test), src/benchmark.py (benchmark_pipeline,
throughput, size_overhead), src/dna_transform.py (dna_transform, used only
to build the post_dna-stage avalanche closure below -- the actual pipeline
run itself always goes through src/pipeline.py).

This script implements two carried-forward design decisions from
docs/raport.md (M4 and M5 sections) that were explicitly queued for M6,
plus one new wrinkle. All three are documented in detail below because
they directly shape how the resulting numbers should be read.

--------------------------------------------------------------------------
Decision A -- avalanche_pct is computed per-row, using each row's own
stage output (docs/raport.md's M4 section; docs/reviews/M4_review.md).
--------------------------------------------------------------------------

docs/raport.md's M4 section and docs/reviews/M4_review.md independently
confirmed (three separate ways) that measuring avalanche on the
*full-pipeline* AES-GCM ciphertext is dominated entirely by AES-GCM's
mandatory per-call random nonce: bit-flip vs. no-flip vs. two wholly
unrelated inputs are all statistically indistinguishable at ~50%. That
number means "AES-GCM looks like independent random noise on every call"
(true, and a good property for AES-GCM), not "the DNA transform diffuses a
bit-flip" (which needs a different measurement). Meanwhile,
scripts/measure_dna_transform_avalanche.py showed that avalanche measured
directly on Pipeline A's deterministic, nonce-free `post_dna` output gives
a real, informative ~30-32% diffusion signal.

Rather than pick one measurement and discard the other, this script wires
`avalanche_test` (src/avalanche.py, used completely unmodified) against
*each row's own stage output*:

  - stage == "input":           encrypt_fn is the identity function
                                 (returns its argument unchanged). This
                                 measures original-vs-bit-flipped-original
                                 directly, with no transform involved at
                                 all. Result is necessarily a small
                                 percentage (one flipped bit out of the
                                 whole byte string) -- this is an EXPECTED
                                 trivial baseline, not an error or a sign
                                 the harness is broken. It exists so the
                                 table shows, in the same column, what "no
                                 transform yet" looks like next to what
                                 each real stage produces.
  - stage == "post_dna"         encrypt_fn = dna_transform(d, ref_seq).
    (Pipeline A only):          Deterministic, no nonce -- this
                                 reproduces the real ~30-32% diffusion
                                 signal documented in docs/raport.md's M4
                                 follow-up section and
                                 scripts/measure_dna_transform_avalanche.py.
  - stage == "post_classical"   encrypt_fn runs the corresponding full
    (both pipelines):           pipeline and returns
                                 post_classical["ciphertext"] (body only,
                                 same convention already used in
                                 tests/test_avalanche.py). Because AES-GCM
                                 draws a fresh random nonce every call,
                                 this naturally reproduces the ~50%
                                 nonce-dominated number for both
                                 pipelines -- expected, and it should NOT
                                 be read as evidence of the DNA transform's
                                 diffusion (see docs/raport.md's M4
                                 section); it is evidence that AES-GCM's
                                 output is semantically secure regardless
                                 of what feeds it.

All three end up as the same `avalanche_pct` column, correctly
disambiguated by the existing `stage` column -- no redundant/confusing
extra columns, and the reader gets the complete picture (trivial baseline,
real transform-diffusion signal, and nonce-driven ciphertext behaviour)
in one place, each attributed to the stage that actually produced it.

--------------------------------------------------------------------------
Decision B -- size overhead is reported as two separate columns, every row
(docs/raport.md's M5 section; docs/test_raport.md's M5 follow-up;
scripts/check_aead_overhead_convention.py).
--------------------------------------------------------------------------

docs/raport.md's M5 section and the standards check in
scripts/check_aead_overhead_convention.py (Wikipedia's "Ciphertext
expansion" article; Go's crypto/cipher AEAD interface docs) established
that AES-GCM's ciphertext body is always exactly the same length as its
plaintext (CTR-mode keystream XOR, no block padding) -- so "size
overhead" computed against the ciphertext body alone is mathematically
guaranteed to read ~0% for every real input, while computing it against
`nonce + ciphertext + tag` (the actually-transmitted/stored unit, per
src/pipeline.py's post_classical stage) gives the real, size-dependent
overhead.

This script reuses `size_overhead()` from src/benchmark.py completely
unmodified -- only what bytes get passed to it changes, exactly like
scripts/check_aead_overhead_convention.py already demonstrated. Two
columns are computed for every row:

  - size_overhead_body_pct:      len(stage's literal output bytes) vs.
                                  len(original input), as a plain length
                                  comparison. For "input" this is
                                  len(data) vs. len(data) = 0% trivially.
                                  For "post_dna" this is 0% because the
                                  byte<->DNA<->byte round trip preserves
                                  length exactly. For "post_classical"
                                  this is 0% because AES-GCM's ciphertext
                                  body is exactly as long as what it
                                  encrypted. Expected to be ~0% (up to
                                  floating point) everywhere -- this is
                                  the mathematically-guaranteed-uninformative
                                  number the M5 finding warned about, kept
                                  here for completeness/comparison, not as
                                  the number to cite.
  - size_overhead_full_aead_pct: same as size_overhead_body_pct for
                                  "input" and "post_dna" (no nonce/tag
                                  exist yet at those stages), but at
                                  "post_classical" it is computed against
                                  `nonce + ciphertext + tag` instead of the
                                  ciphertext alone -- this is the real,
                                  size-dependent number (large relative
                                  overhead on small inputs, near-negligible
                                  on large ones, per
                                  scripts/check_aead_overhead_convention.py).
                                  This is the number that should be cited
                                  for AES-GCM's actual on-wire/on-disk
                                  cost.

--------------------------------------------------------------------------
New wrinkle -- timing/throughput convention at the "input" stage.
--------------------------------------------------------------------------

There is no real "processing time" to reach the raw `input` stage: it is
just the corpus file's own bytes, produced by 0 ms of pipeline work, by
construction. src/benchmark.py's throughput() deliberately raises
ValueError for a zero or negative duration (it has no meaningful
bytes/sec to report for a duration that didn't happen), and the exit
criteria for this milestone forbid any null/NaN value anywhere in the
CSV. Silently feeding it 0.0 ms would either crash (ValueError) or,
if worked around carelessly, produce a divide-by-zero-flavoured
`inf`/nonsense figure.

Decision taken here (documented, not silently guessed at): at the
"input" stage, `dna_transform_ms`, `classical_encrypt_ms`, and `total_ms`
are all set to the literal `0.0` -- truthfully, no transform/encryption
has run yet at this stage, so 0 ms elapsed is not a placeholder, it is
the correct answer. `throughput_bytes_per_sec` is then set to an explicit
`0.0` sentinel as well, rather than calling `throughput()` (which would
raise on total_ms <= 0) or inventing a large/undefined number. This 0.0
is documented here as meaning "not applicable / no processing occurred
yet to have a rate," not "this stage processes at zero bytes/sec" --
readers of results/experiment_results.csv and docs/findings.md should
treat every `input`-stage throughput value as this explicit sentinel, not
as a real measured rate. Every other stage (post_dna, post_classical) has
a genuine nonzero total_ms and gets a real throughput() value computed
from it.

For post_dna and post_classical rows, `total_ms` is reported as the
CUMULATIVE median time to reach that stage's output from the raw input
(i.e. post_dna's total_ms is just the DNA-transform stage's own median
time; post_classical's total_ms is benchmark_pipeline's own full
end-to-end `total_ms`, which already covers both stages for Pipeline A).
This makes `total_ms` directly usable as "time elapsed to produce this
stage's bytes," which is the throughput()-compatible quantity, rather
than re-summing independently-sampled per-stage medians (which
docs/reviews/M5_review.md already noted don't sum exactly to
`total_ms` due to being separate median samples -- using
benchmark_pipeline's own `total_ms` directly for the final stage avoids
compounding that discrepancy here).

Run from the `project/` directory:
    /Users/sophiepopow/Documents/PK/master/dna/.venv/bin/python scripts/run_experiment.py
"""

import csv
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from avalanche import avalanche_test
from benchmark import benchmark_pipeline, size_overhead, throughput
from dna_transform import dna_transform
from metrics import chi_square_uniform, compression_ratio, pearson_correlation, shannon_entropy
from pipeline import pipeline_a_dna_plus_classical, pipeline_b_classical_only

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
CORPUS_DIR = os.path.join(DATA_DIR, "corpus")
RESULTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "results"))
OUTPUT_CSV = os.path.join(RESULTS_DIR, "experiment_results.csv")

N_REPS = 20
N_TRIALS_AVALANCHE = 25

# (filename, data_class, size_class) -- the 6 frozen corpus files, per
# docs/scope.md / M3's baseline_entropy.csv.
CORPUS_FILES = [
    ("text_small.txt", "text", "small"),
    ("text_large.txt", "text", "large"),
    ("json_small.json", "json", "small"),
    ("json_large.json", "json", "large"),
    ("random_small.bin", "random", "small"),
    ("random_large.bin", "random", "large"),
]

CSV_FIELDNAMES = [
    "file",
    "data_class",
    "size_class",
    "pipeline",
    "stage",
    "input_size_bytes",
    "stage_size_bytes",
    "entropy_bits_per_byte",
    "chi_square_statistic",
    "compression_ratio",
    "correlation_vs_input",
    "avalanche_pct",
    "dna_transform_ms",
    "classical_encrypt_ms",
    "total_ms",
    "throughput_bytes_per_sec",
    "size_overhead_body_pct",
    "size_overhead_full_aead_pct",
]


def _load_key() -> bytes:
    with open(os.path.join(DATA_DIR, "aes_key.bin"), "rb") as f:
        return f.read()


def _load_reference_sequence() -> str:
    with open(os.path.join(DATA_DIR, "reference_sequence.txt")) as f:
        return f.read().strip()


def _load_corpus_file(name: str) -> bytes:
    with open(os.path.join(CORPUS_DIR, name), "rb") as f:
        return f.read()


def _stage_metric_bytes(stage: str, stages: dict) -> bytes:
    """
    The bytes M4's four metrics (entropy, chi-square, compression,
    correlation) are computed against for a given stage. For
    post_classical, this is the ciphertext BODY only (excluding
    nonce/tag) -- the same convention already established in
    tests/test_avalanche.py and scripts/measure_dna_transform_avalanche.py
    for "the ciphertext" as a semantic payload, kept consistent here.
    Size-overhead accounting (Decision B, module docstring) is handled
    separately and does look at the nonce+tag too.
    """
    if stage == "input":
        return stages["input"]
    if stage == "post_dna":
        return stages["post_dna"]
    if stage == "post_classical":
        return stages["post_classical"]["ciphertext"]
    raise ValueError(f"unknown stage: {stage}")


def _full_aead_bytes(stages: dict) -> bytes:
    pc = stages["post_classical"]
    return pc["nonce"] + pc["ciphertext"] + pc["tag"]


def _make_avalanche_fn(pipeline: str, stage: str, key: bytes, reference_sequence: str):
    """
    Build the one-argument encrypt_fn avalanche_test needs (see
    src/avalanche.py's docstring for that interface), per Decision A
    above: each stage gets its OWN natural encrypt_fn, not a shared one.
    """
    if stage == "input":
        return lambda d: d
    if stage == "post_dna":
        return lambda d: dna_transform(d, reference_sequence)
    if stage == "post_classical":
        if pipeline == "A":
            return lambda d: pipeline_a_dna_plus_classical(d, key, reference_sequence)[
                "post_classical"
            ]["ciphertext"]
        else:
            return lambda d: pipeline_b_classical_only(d, key)["post_classical"]["ciphertext"]
    raise ValueError(f"unknown stage: {stage}")


def _timing_and_throughput(stage: str, bench: dict, input_size: int):
    """
    Implements the "new wrinkle" convention documented in this module's
    docstring: 0.0/0.0/0.0/0.0 (sentinel) at the input stage, cumulative
    real timings + a real throughput() value at every later stage.
    """
    if stage == "input":
        return 0.0, 0.0, 0.0, 0.0  # dna_ms, classical_ms, total_ms, throughput sentinel

    if stage == "post_dna":
        dna_ms = bench["dna_transform_ms"]
        classical_ms = 0.0
        total_ms = dna_ms
    elif stage == "post_classical":
        dna_ms = bench["dna_transform_ms"]
        classical_ms = bench["classical_encrypt_ms"]
        total_ms = bench["total_ms"]
    else:
        raise ValueError(f"unknown stage: {stage}")

    tput = throughput(input_size, total_ms) if total_ms > 0 else 0.0
    return dna_ms, classical_ms, total_ms, tput


def _build_row(
    filename: str,
    data_class: str,
    size_class: str,
    pipeline: str,
    stage: str,
    data: bytes,
    stages: dict,
    bench: dict,
    key: bytes,
    reference_sequence: str,
) -> dict:
    input_size = len(data)
    stage_bytes = _stage_metric_bytes(stage, stages)

    entropy = shannon_entropy(stage_bytes)
    chi2 = chi_square_uniform(stage_bytes)
    comp_ratio = compression_ratio(stage_bytes)
    corr = pearson_correlation(data, stage_bytes)

    avalanche_fn = _make_avalanche_fn(pipeline, stage, key, reference_sequence)
    avalanche_pct = avalanche_test(avalanche_fn, data, n_trials=N_TRIALS_AVALANCHE)

    dna_ms, classical_ms, total_ms, tput = _timing_and_throughput(stage, bench, input_size)

    # Decision B: both size-overhead conventions, every row.
    overhead_body_pct = size_overhead(data, stage_bytes)
    if stage == "post_classical":
        overhead_full_aead_pct = size_overhead(data, _full_aead_bytes(stages))
    else:
        overhead_full_aead_pct = overhead_body_pct

    return {
        "file": filename,
        "data_class": data_class,
        "size_class": size_class,
        "pipeline": pipeline,
        "stage": stage,
        "input_size_bytes": input_size,
        "stage_size_bytes": len(stage_bytes),
        "entropy_bits_per_byte": entropy,
        "chi_square_statistic": chi2,
        "compression_ratio": comp_ratio,
        "correlation_vs_input": corr,
        "avalanche_pct": avalanche_pct,
        "dna_transform_ms": dna_ms,
        "classical_encrypt_ms": classical_ms,
        "total_ms": total_ms,
        "throughput_bytes_per_sec": tput,
        "size_overhead_body_pct": overhead_body_pct,
        "size_overhead_full_aead_pct": overhead_full_aead_pct,
    }


def run():
    key = _load_key()
    reference_sequence = _load_reference_sequence()

    rows = []
    t_start = time.perf_counter()

    for filename, data_class, size_class in CORPUS_FILES:
        data = _load_corpus_file(filename)
        print(f"\n=== {filename} ({len(data)} bytes, class={data_class}/{size_class}) ===")

        # --- Pipeline A: DNA transform + AES-GCM ---
        t0 = time.perf_counter()
        stages_a = pipeline_a_dna_plus_classical(data, key, reference_sequence)
        bench_a = benchmark_pipeline(
            pipeline_a_dna_plus_classical, data, key, n_reps=N_REPS, reference_sequence=reference_sequence
        )
        for stage in ("input", "post_dna", "post_classical"):
            rows.append(
                _build_row(
                    filename, data_class, size_class, "A", stage, data, stages_a, bench_a, key, reference_sequence
                )
            )
        print(f"  Pipeline A done in {time.perf_counter() - t0:.2f}s")

        # --- Pipeline B: AES-GCM only (control) ---
        t0 = time.perf_counter()
        stages_b = pipeline_b_classical_only(data, key)
        bench_b = benchmark_pipeline(pipeline_b_classical_only, data, key, n_reps=N_REPS)
        for stage in ("input", "post_classical"):
            rows.append(
                _build_row(
                    filename, data_class, size_class, "B", stage, data, stages_b, bench_b, key, reference_sequence
                )
            )
        print(f"  Pipeline B done in {time.perf_counter() - t0:.2f}s")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"\nWrote {len(rows)} rows to {OUTPUT_CSV}")
    print(f"Total experiment run time: {time.perf_counter() - t_start:.2f}s")


if __name__ == "__main__":
    run()
