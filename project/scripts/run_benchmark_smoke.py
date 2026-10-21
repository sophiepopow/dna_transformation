"""
scripts/run_benchmark_smoke.py

Smoke test for the M5 benchmark harness (src/benchmark.py): runs it once on
data/corpus/text_small.txt for both experimental pipelines and prints the
per-stage timings, throughput, and ciphertext size overhead to the console.

This is a manual/CI sanity check, not a pytest suite (see
tests/test_benchmark.py for the real assertions) -- its job is just to
confirm the harness runs end-to-end without error and produces non-zero,
finite numbers for both pipelines, per M5's exit criteria.

Run from the `project/` directory:
    python3 scripts/run_benchmark_smoke.py
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from benchmark import benchmark_pipeline, throughput, size_overhead
from pipeline import pipeline_a_dna_plus_classical, pipeline_b_classical_only

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
CORPUS_DIR = os.path.join(DATA_DIR, "corpus")

with open(os.path.join(DATA_DIR, "aes_key.bin"), "rb") as f:
    KEY = f.read()
with open(os.path.join(DATA_DIR, "reference_sequence.txt")) as f:
    REFERENCE_SEQUENCE = f.read().strip()
with open(os.path.join(CORPUS_DIR, "text_small.txt"), "rb") as f:
    TEXT_SMALL = f.read()


def _print_result(label: str, result: dict, data_size_bytes: int, ciphertext: bytes):
    print(f"\n--- {label} ---")
    print(f"  dna_transform_ms:     {result['dna_transform_ms']:.4f} ms")
    print(f"  classical_encrypt_ms: {result['classical_encrypt_ms']:.4f} ms")
    print(f"  total_ms:             {result['total_ms']:.4f} ms")

    tput = throughput(data_size_bytes, result["total_ms"])
    print(f"  throughput:           {tput:,.2f} bytes/sec")

    overhead = size_overhead(TEXT_SMALL, ciphertext)
    print(f"  size_overhead:        {overhead:.4f} %")


if __name__ == "__main__":
    print(f"Benchmarking on data/corpus/text_small.txt ({len(TEXT_SMALL)} bytes)")

    result_a = benchmark_pipeline(
        pipeline_a_dna_plus_classical,
        TEXT_SMALL,
        KEY,
        n_reps=20,
        reference_sequence=REFERENCE_SEQUENCE,
    )
    stages_a = pipeline_a_dna_plus_classical(TEXT_SMALL, KEY, REFERENCE_SEQUENCE)
    _print_result(
        "Pipeline A (DNA transform + AES-GCM)",
        result_a,
        len(TEXT_SMALL),
        stages_a["post_classical"]["ciphertext"],
    )

    result_b = benchmark_pipeline(pipeline_b_classical_only, TEXT_SMALL, KEY, n_reps=20)
    stages_b = pipeline_b_classical_only(TEXT_SMALL, KEY)
    _print_result(
        "Pipeline B (AES-GCM only, control)",
        result_b,
        len(TEXT_SMALL),
        stages_b["post_classical"]["ciphertext"],
    )

    print("\nSmoke test complete: harness ran without error for both pipelines.")
