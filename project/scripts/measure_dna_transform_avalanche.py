"""
scripts/measure_dna_transform_avalanche.py

Follow-up to the M4 finding (see docs/reviews/M4_review.md and
docs/raport.md's M4 section) that avalanche_test, when wired against the
full pipeline's AES-GCM ciphertext, mostly measures AES-GCM's mandatory
per-call nonce randomization rather than genuine bit-flip sensitivity.

This script measures avalanche on Pipeline A's *pre-AES* stage instead —
the DNA-transform's own output (`post_dna`) — where there is no nonce to
confound the result, since the chained mod-4 transform (src/dna_transform.py)
is fully deterministic. This reuses the existing, unmodified
avalanche_test(pipeline_encrypt_fn, data, n_trials) from src/avalanche.py;
only the wrapped "encrypt" function changes (it returns post_dna bytes
instead of the AES-GCM ciphertext body).

A single run of 25 trials showed high variance (min 3%, max 70%) during
M4's investigation, so this script runs many independent batches to give a
more stable, citable mean +/- standard deviation rather than a single noisy
number.

Run from the `project/` directory:
    python3 scripts/measure_dna_transform_avalanche.py
"""
import os
import sys
import statistics

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from avalanche import avalanche_test
from pipeline import pipeline_a_dna_plus_classical

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
CORPUS_DIR = os.path.join(DATA_DIR, "corpus")

with open(os.path.join(DATA_DIR, "aes_key.bin"), "rb") as f:
    KEY = f.read()
with open(os.path.join(DATA_DIR, "reference_sequence.txt")) as f:
    REFERENCE_SEQUENCE = f.read().strip()


def encrypt_dna_only(data: bytes) -> bytes:
    stages = pipeline_a_dna_plus_classical(data, KEY, REFERENCE_SEQUENCE)
    return stages["post_dna"]


def measure(filename: str, n_batches: int = 20, n_trials_per_batch: int = 100):
    with open(os.path.join(CORPUS_DIR, filename), "rb") as f:
        data = f.read()

    batch_means = [
        avalanche_test(encrypt_dna_only, data, n_trials=n_trials_per_batch)
        for _ in range(n_batches)
    ]
    mean = statistics.mean(batch_means)
    stdev = statistics.stdev(batch_means)
    print(
        f"{filename:16s} | {n_batches} batches x {n_trials_per_batch} trials "
        f"= {n_batches * n_trials_per_batch} total flips | "
        f"mean={mean:.2f}%  stdev={stdev:.2f}%  min={min(batch_means):.2f}%  max={max(batch_means):.2f}%"
    )


if __name__ == "__main__":
    measure("text_small.txt")
    measure("json_small.json")
    measure("random_small.bin")
