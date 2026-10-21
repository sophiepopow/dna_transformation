"""
scripts/measure_avalanche_by_flip_position.py

Task 3 of the reference-sequence factorial follow-up: Section 7.5 reports
one averaged post_dna avalanche figure (30-32%), which Task 2's mechanism
check confirmed is an average over flip positions ranging from ~62%
avalanche (a flip near the very start, almost the whole stream is
"downstream") down to near 0% (a flip near the very end, almost nothing
is downstream). This script measures that decline directly instead of
only averaging over it.

Interpretation of "flip position at X% of the input": the flipped bit is
chosen within the byte at index round(X% * len(data)), picked uniformly
at random among that byte's 8 bits across trials (byte-level target,
bit-level randomization within it) -- a natural granularity given the
transform's 4-nucleotide-per-byte packing, and one that does not require
choosing a single, arbitrary fixed bit position.

Reuses, unmodified: src/dna_transform.py's dna_transform,
src/avalanche.py's _hamming_distance_bits (the same Hamming-distance
implementation avalanche_test itself uses, not a reimplementation).

Run from the `project/` directory:
    python3 scripts/measure_avalanche_by_flip_position.py
"""

import csv
import os
import random
import statistics
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from avalanche import _hamming_distance_bits  # noqa: E402
from dna_transform import dna_transform  # noqa: E402

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
CORPUS_DIR = os.path.join(DATA_DIR, "corpus")
RESULTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "results"))
OUTPUT_CSV = os.path.join(RESULTS_DIR, "avalanche_by_flip_position.csv")

FLIP_POSITIONS_PCT = [1, 10, 25, 50, 75, 90, 99]
N_TRIALS = 300


def _load_reference_sequence() -> str:
    with open(os.path.join(DATA_DIR, "reference_sequence.txt")) as f:
        return f.read().strip().upper()


def _load_corpus_file(name: str) -> bytes:
    with open(os.path.join(CORPUS_DIR, name), "rb") as f:
        return f.read()


def _trial(data: bytes, reference_sequence: str, target_byte_index: int, rng: random.Random) -> float:
    bit_in_byte = rng.randrange(8)
    flipped = bytearray(data)
    flipped[target_byte_index] ^= 1 << bit_in_byte
    flipped = bytes(flipped)

    original_out = dna_transform(data, reference_sequence)
    flipped_out = dna_transform(flipped, reference_sequence)

    n_bits = min(len(original_out), len(flipped_out)) * 8
    diff = _hamming_distance_bits(original_out[: n_bits // 8], flipped_out[: n_bits // 8])
    return 100.0 * diff / n_bits


def run():
    reference_sequence = _load_reference_sequence()
    data = _load_corpus_file("text_small.txt")
    rng = random.Random(20260906)

    rows = []
    print(f"Avalanche by flip position, text_small.txt ({len(data)} bytes), "
          f"{N_TRIALS} trials per position")
    for pct in FLIP_POSITIONS_PCT:
        target_byte_index = min(len(data) - 1, max(0, round(pct / 100 * len(data))))
        percentages = [_trial(data, reference_sequence, target_byte_index, rng) for _ in range(N_TRIALS)]
        mean = statistics.mean(percentages)
        stdev = statistics.stdev(percentages)
        print(f"  flip @ {pct:3d}% (byte {target_byte_index:5d}/{len(data)}): "
              f"mean={mean:.2f}%  stdev={stdev:.2f}%")
        rows.append({"flip_position_pct": pct, "mean_avalanche_pct": mean, "stdev": stdev})

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["flip_position_pct", "mean_avalanche_pct", "stdev"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    print(f"\nWrote {len(rows)} rows to {OUTPUT_CSV}")


if __name__ == "__main__":
    run()
