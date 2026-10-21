"""
scripts/measure_entropy_periodicity.py

Independent verification script for M1's chained mod-4 DNA transform
(src/dna_transform.py). Written during the M1 milestone review, not part
of the pytest suite (tests/test_dna_transform.py) — this exists so the
entropy-gap and periodicity-leak numbers backing the M1 design decision
can be reproduced/re-measured later (e.g. reused or extended for the M6
statistical analysis and cited directly in the thesis).

What it measures, and why:

1. Shannon entropy (bits/byte) of the dna_transform() output for a few
   sample byte streams of different "structuredness": JSON-like text,
   plain English text, and os.urandom (already-random) bytes. This is
   the core signal the thesis depends on: structured/low-entropy input
   should transform to measurably lower entropy output than
   already-random/high-entropy input. If all three converge to the same
   near-maximal entropy, the transform is destroying the entropy-class
   signal (this happened with the earlier SHA-256-mask design).

2. Lag-`period` byte-XOR-preservation ratio: the fraction of byte pairs
   (i, i+period) where ciphertext[i] XOR ciphertext[i+period] equals
   plaintext[i] XOR plaintext[i+period]. period = len(reference
   sequence) in bytes (64 nt / 4 nt-per-byte = 16 bytes). A ratio near
   chance level (~1/256 ~= 0.004) means no periodicity leak. A ratio
   near 1.0 means the ciphertext trivially reveals the reference
   sequence's period without knowing the plaintext (this happened with
   the earlier tiled-mask + fixed-rotation design, ratio ~0.835).

Uses only the standard library (math, os, random, sys) — no numpy/scipy
— matching the dependency footprint of the test suite itself.

Run from the `project/` directory:
    python3 scripts/measure_entropy_periodicity.py
"""

import sys
import os
import math
import random

sys.path.insert(0, "src")

from dna_transform import dna_transform

REFERENCE_SEQUENCE = "AACTTTAAGAAATTATGTGCATGCCTTCAAGACCCAGAGACCTAATCATAGCGCTCCTCATTTG"  # 64 nt, fixed
assert len(REFERENCE_SEQUENCE) == 64


def shannon_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = [0] * 256
    for b in data:
        counts[b] += 1
    n = len(data)
    h = 0.0
    for c in counts:
        if c:
            p = c / n
            h -= p * math.log2(p)
    return h


def periodicity_preserved_ratio(plain: bytes, cipher: bytes, period_bytes: int) -> float:
    n_check = len(plain) - period_bytes
    if n_check <= 0:
        return float("nan")
    preserved = sum(
        1 for i in range(n_check)
        if (cipher[i] ^ cipher[i + period_bytes]) == (plain[i] ^ plain[i + period_bytes])
    )
    return preserved / n_check


def main():
    random.seed(42)

    # ~4000-byte structured JSON-like sample
    text_sample = (
        "{\"user\": \"alice\", \"action\": \"login\", \"timestamp\": 1734000000, "
        "\"ip\": \"10.0.0.42\", \"status\": \"ok\", \"session\": \"abcde12345\"} " * 60
    ).encode("utf-8")[:4000]

    # ~4000-byte plain English text sample
    english_sample = (
        "In the beginning of the thesis we describe a DNA encoding transform "
        "applied to structured and unstructured data of varying entropy classes. " * 30
    ).encode("utf-8")[:4000]

    # ~4000-byte already-random sample
    random_sample = os.urandom(4000)

    period_bytes = len(REFERENCE_SEQUENCE) // 4  # 16

    print(f"Reference sequence length: {len(REFERENCE_SEQUENCE)} nt -> period_bytes = {period_bytes}")
    print()

    for name, sample in [
        ("JSON-like", text_sample),
        ("English text", english_sample),
        ("os.urandom", random_sample),
    ]:
        cipher = dna_transform(sample, REFERENCE_SEQUENCE)
        h_plain = shannon_entropy(sample)
        h_cipher = shannon_entropy(cipher)
        ratio = periodicity_preserved_ratio(sample, cipher, period_bytes)
        print(
            f"{name:14s} | len={len(sample):5d} | H(plain)={h_plain:.3f} bits/byte | "
            f"H(cipher)={h_cipher:.3f} bits/byte | lag-{period_bytes} XOR-preserved ratio={ratio:.4f}"
        )

    print()
    print("Reference (M1 revision report) claims: text ~7.27, random ~7.95 bits/byte; "
          "periodicity leak ratio ~0.017 (vs ~0.835 for the old tiled-mask design).")


if __name__ == "__main__":
    main()
