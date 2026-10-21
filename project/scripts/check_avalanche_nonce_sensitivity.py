"""
scripts/check_avalanche_nonce_sensitivity.py

Independent verification script for M4's avalanche_test (src/avalanche.py).
Written during M4 implementation to investigate a real methodological
question: does avalanche_test's ~40-60% Hamming-distance result (using the
pipelines' natural random-nonce AES-GCM behavior) actually come from the
one-bit flip being tested, or just from AES-GCM generating a fresh random
nonce on every call regardless of whether anything was flipped at all?

Compares:
  (a) original vs. a genuinely bit-flipped copy (what avalanche_test does)
  (b) original vs. an UNMODIFIED copy of the exact same data (no bit flip)

If (a) and (b) give roughly the same ~40-60% Hamming distance, the metric
is dominated by nonce randomization, not genuine input sensitivity — the
same class of "test passes on paper for the wrong reason" issue this
project hit once before with M1's SHA-256 mask design (see docs/raport.md).

Run from the `project/` directory:
    python3 scripts/check_avalanche_nonce_sensitivity.py
"""
import os
import sys
import random

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from pipeline import pipeline_a_dna_plus_classical, pipeline_b_classical_only

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))

with open(os.path.join(DATA_DIR, "aes_key.bin"), "rb") as f:
    KEY = f.read()
with open(os.path.join(DATA_DIR, "reference_sequence.txt")) as f:
    REFERENCE_SEQUENCE = f.read().strip()
with open(os.path.join(DATA_DIR, "corpus", "text_small.txt"), "rb") as f:
    TEXT_SMALL = f.read()


def encrypt_a(data):
    return pipeline_a_dna_plus_classical(data, KEY, REFERENCE_SEQUENCE)["post_classical"]["ciphertext"]


def encrypt_b(data):
    return pipeline_b_classical_only(data, KEY)["post_classical"]["ciphertext"]


def hamming_distance_bits(a, b):
    n = min(len(a), len(b))
    return sum(bin(x ^ y).count("1") for x, y in zip(a[:n], b[:n])), n * 8


def mean_pct(fn_pairs, n_trials=25):
    pcts = []
    for _ in range(n_trials):
        a, b = fn_pairs()
        dist, n_bits = hamming_distance_bits(a, b)
        pcts.append(100.0 * dist / n_bits)
    return sum(pcts) / len(pcts)


def flip_one_bit(data):
    flipped = bytearray(data)
    bit_index = random.randrange(len(data) * 8)
    byte_index, bit_in_byte = divmod(bit_index, 8)
    flipped[byte_index] ^= 1 << bit_in_byte
    return bytes(flipped)


def main():
    random.seed(123)

    for name, encrypt_fn in [("Pipeline A", encrypt_a), ("Pipeline B", encrypt_b)]:
        def cond_a():
            flipped = flip_one_bit(TEXT_SMALL)
            return encrypt_fn(TEXT_SMALL), encrypt_fn(flipped)

        def cond_b():
            return encrypt_fn(TEXT_SMALL), encrypt_fn(TEXT_SMALL)

        pct_a = mean_pct(cond_a)
        pct_b = mean_pct(cond_b)
        print(f"{name}: bit-flip condition (a) = {pct_a:.2f}%  |  no-flip condition (b) = {pct_b:.2f}%")


if __name__ == "__main__":
    main()
