"""
src/benchmark.py

Performance benchmark harness for the DNA-encoding statistical impact study.
Measures per-stage execution time, throughput, and ciphertext size overhead
with repeated runs and robust (median/IQR) statistics, so results are
comparable to the reference metric set used in lightweight-cipher
performance reporting (see this milestone's reference paper, the NIST
lightweight-crypto/ASCON survey: https://arxiv.org/abs/2304.06222).

Functions:
- time_stage(fn, *args, n_reps=20)            -> {"median_ms", "iqr_ms",
                                                    "all_samples"}
- benchmark_pipeline(pipeline_fn, data, key,
                      n_reps=20,
                      reference_sequence=None) -> {"dna_transform_ms",
                                                    "classical_encrypt_ms",
                                                    "total_ms", ...}
- throughput(data_size_bytes, total_ms)        -> bytes/sec (float)
- size_overhead(plaintext, ciphertext)         -> percentage increase (float)

--- Design point: benchmark_pipeline's signature vs. the real pipelines ---

The milestone spec's literal signature is
`benchmark_pipeline(pipeline_fn, data, key, n_reps=20) -> dict`, with a
single opaque `pipeline_fn`. Two problems with taking that completely
literally, both discovered by trying to actually call it:

1. The required return shape (`dna_transform_ms`, `classical_encrypt_ms`,
   `total_ms`) needs real stage-level timings. A single opaque call to
   `pipeline_a_dna_plus_classical` / `pipeline_b_classical_only` only ever
   gives one end-to-end duration — it cannot be decomposed into per-stage
   numbers after the fact. Resolution: `time_stage` is applied directly to
   the underlying stage functions (`dna_transform`, `encrypt_aes_gcm`,
   imported straight from their modules) to get real, independently-timed
   per-stage numbers, *in addition to* one direct `time_stage` call on
   `pipeline_fn` itself for `total_ms`.

2. `pipeline_a_dna_plus_classical(data, key, reference_sequence)` takes a
   required third argument that `pipeline_b_classical_only(data, key)`
   does not have. A 3-argument `(pipeline_fn, data, key)` signature cannot
   call Pipeline A at all (missing required argument), so the literal
   4-parameter spec signature is not actually callable against both real
   pipelines as written. Resolution: an optional keyword-only
   `reference_sequence: str = None` parameter is added. When provided,
   `pipeline_fn` is called as `pipeline_fn(data, key, reference_sequence)`
   (Pipeline A's shape) and the DNA-transform stage is timed directly via
   `dna_transform(data, reference_sequence)`. When omitted (`None`),
   `pipeline_fn` is called as `pipeline_fn(data, key)` (Pipeline B's shape)
   and there is no DNA stage to time.

   `reference_sequence=None` also doubles as the signal for which branch
   to take, so the caller doesn't need to separately declare "this is
   Pipeline A/B" — passing the fixed experiment reference sequence *is*
   the declaration. This mirrors the same kind of necessary signature
   adaptation already documented for `avalanche_test` in
   `src/avalanche.py` (there resolved via a caller-side one-argument
   closure instead; here resolved via an optional kwarg so
   `benchmark_pipeline` can still decide, on its own, whether to run the
   DNA sub-timing).

3. Pipeline B has no DNA-transform stage at all. `dna_transform_ms` is set
   to `0.0` (not omitted) when `reference_sequence` is `None`, so that
   every returned dict has the same fixed key set regardless of pipeline,
   which is friendlier to downstream tabular use (e.g. M6's per-row CSV
   export) than a key that sometimes exists and sometimes doesn't. Callers
   that need to tell "no DNA stage" apart from "a DNA stage that happened
   to time near zero" can do so via the `dna_transform_stats` value, which
   is `None` for Pipeline B and a full `time_stage` dict for Pipeline A.
"""

import time
import statistics

import numpy as np

from classical_crypto import encrypt_aes_gcm
from dna_transform import dna_transform


def time_stage(fn, *args, n_reps: int = 20) -> dict:
    """
    Time `n_reps` repeated calls of `fn(*args)` using time.perf_counter(),
    discarding the first ("warm-up") run.

    A total of n_reps + 1 calls are made: 1 warm-up call (discarded) plus
    n_reps measured calls, so the caller always gets exactly n_reps timed
    samples regardless of warm-up cost. This is the standard
    warm-up-then-measure micro-benchmark pattern; the alternative reading
    (n_reps calls total, first discarded, leaving n_reps - 1 samples) would
    make the number of usable samples depend on n_reps in a way that felt
    like an avoidable off-by-one surprise for callers, so it was not used.

    Returns {"median_ms": ..., "iqr_ms": ..., "all_samples": [...]} where
    "all_samples" holds the n_reps post-warm-up sample durations in
    milliseconds (the discarded warm-up sample is not included).
    """
    samples_ms = []
    for _ in range(n_reps + 1):
        start = time.perf_counter()
        fn(*args)
        end = time.perf_counter()
        samples_ms.append((end - start) * 1000.0)

    timed = samples_ms[1:]  # discard first run (warm-up)

    median_ms = statistics.median(timed)
    q75, q25 = np.percentile(timed, [75, 25])
    iqr_ms = float(q75 - q25)

    return {"median_ms": median_ms, "iqr_ms": iqr_ms, "all_samples": timed}


def benchmark_pipeline(
    pipeline_fn,
    data: bytes,
    key: bytes,
    n_reps: int = 20,
    reference_sequence: str = None,
) -> dict:
    """
    Benchmark one full pipeline call plus its individual stages.

    `pipeline_fn` must be one of the two project pipeline functions
    (src/pipeline.py):
      - pipeline_b_classical_only(data, key) -> stages dict
          -> call with reference_sequence=None (the default)
      - pipeline_a_dna_plus_classical(data, key, reference_sequence) -> stages dict
          -> call with reference_sequence=<the fixed experiment sequence>

    See this module's docstring ("Design point") for why `reference_sequence`
    exists as an extra optional parameter beyond the milestone spec's
    literal 4-argument signature, and why it doubles as the Pipeline A vs.
    B switch.

    Returns a dict with (at minimum):
        "dna_transform_ms":    median ms for dna_transform alone
                                (0.0 if reference_sequence is None, i.e.
                                Pipeline B has no DNA stage)
        "classical_encrypt_ms": median ms for encrypt_aes_gcm alone
        "total_ms":             median ms for one full pipeline_fn call
    plus the full time_stage dicts behind each of those medians
    ("dna_transform_stats", "classical_encrypt_stats", "total_stats") for
    callers (e.g. a later M6 script) that want IQR / all_samples too.
    "dna_transform_stats" is None when there is no DNA stage.
    """
    if reference_sequence is not None:
        dna_stats = time_stage(dna_transform, data, reference_sequence, n_reps=n_reps)
        dna_transform_ms = dna_stats["median_ms"]
        # Time the classical-encryption stage on the actual post-DNA bytes
        # Pipeline A would feed it, not the raw input, so the stage timing
        # reflects what really happens inside the pipeline.
        post_dna = dna_transform(data, reference_sequence)
        classical_stats = time_stage(encrypt_aes_gcm, post_dna, key, n_reps=n_reps)
        total_stats = time_stage(pipeline_fn, data, key, reference_sequence, n_reps=n_reps)
    else:
        dna_stats = None
        dna_transform_ms = 0.0
        classical_stats = time_stage(encrypt_aes_gcm, data, key, n_reps=n_reps)
        total_stats = time_stage(pipeline_fn, data, key, n_reps=n_reps)

    return {
        "dna_transform_ms": dna_transform_ms,
        "classical_encrypt_ms": classical_stats["median_ms"],
        "total_ms": total_stats["median_ms"],
        "dna_transform_stats": dna_stats,
        "classical_encrypt_stats": classical_stats,
        "total_stats": total_stats,
    }


def throughput(data_size_bytes: int, total_ms: float) -> float:
    """
    Throughput in bytes/sec, given a data size in bytes and a total
    execution time in milliseconds.

    Returns 0.0 if data_size_bytes is 0. Raises ValueError if total_ms is
    not positive (a zero or negative duration cannot yield a meaningful
    rate).
    """
    if data_size_bytes == 0:
        return 0.0
    if total_ms <= 0:
        raise ValueError("total_ms must be positive to compute throughput")
    return data_size_bytes / (total_ms / 1000.0)


def size_overhead(plaintext: bytes, ciphertext: bytes) -> float:
    """
    Percentage increase in size from `plaintext` to `ciphertext`:
    (len(ciphertext) - len(plaintext)) / len(plaintext) * 100.

    Returns 0.0 if plaintext is empty (no baseline size to compute a
    percentage against).
    """
    if len(plaintext) == 0:
        return 0.0
    return (len(ciphertext) - len(plaintext)) / len(plaintext) * 100.0
