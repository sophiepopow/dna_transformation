"""
scripts/verify_prefix_sum_and_avalanche_closed_form.py

Task 2 of the reference-sequence factorial follow-up: independently
verify two analytic claims made in the thesis, against the real
src/dna_transform.py and src/avalanche.py -- not a reimplementation of
either.

Claim 1 (prefix-sum equivalence): dna_transform(data, ref)'s output
nucleotide sequence is exactly a running (prefix) sum of
(plaintext-nucleotide-value + reference-nucleotide-value), taken mod 4.
This follows algebraically from the recurrence
c_i = (p_i + r_{i mod L} + c_{i-1}) mod 4 with c_{-1}=0, but is checked
here empirically against the actual dna_transform() output, not assumed.

Claim 2 (avalanche closed form): the measured 30-32% post_dna avalanche
figure decomposes as (fraction of the stream downstream of the flipped
nucleotide) x (fraction of bits that differ at a nucleotide whose value
has been shifted by a fixed, nonzero mod-4 delta), which theory puts at
approximately 0.5 x 62.5% = 31.25%. This script checks:
  (a) the black-box 2,000-trial post_dna avalanche average reproduces
      the previously-reported 30.4-31.8% range (reusing
      src/avalanche.py's avalanche_test() unmodified, matching
      scripts/measure_dna_transform_avalanche.py's method exactly);
  (b) the underlying mechanism directly: flipping one input bit leaves
      every output nucleotide before the flip position byte-identical,
      and shifts every nucleotide from that position onward by the
      SAME constant value mod 4;
  (c) the two claimed factors (0.5, 62.5%) separately, by measuring, per
      trial, the downstream fraction and the average bit-difference
      fraction restricted to the downstream nucleotides only.

Run from the `project/` directory:
    python3 scripts/verify_prefix_sum_and_avalanche_closed_form.py
"""

import os
import random
import statistics
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from avalanche import avalanche_test  # noqa: E402
from dna_transform import DEFAULT_MAPPING, dna_transform  # noqa: E402
from dna_codec import bits_to_dna, bytes_to_bits  # noqa: E402

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
CORPUS_DIR = os.path.join(DATA_DIR, "corpus")

NT_TO_VAL = {nt: int(bits, 2) for bits, nt in DEFAULT_MAPPING.items()}


def _load_reference_sequence() -> str:
    with open(os.path.join(DATA_DIR, "reference_sequence.txt")) as f:
        return f.read().strip().upper()


def _load_corpus_file(name: str) -> bytes:
    with open(os.path.join(CORPUS_DIR, name), "rb") as f:
        return f.read()


def _nucleotide_values(data: bytes) -> list:
    dna = bits_to_dna(bytes_to_bits(data), DEFAULT_MAPPING)
    return [NT_TO_VAL[ch] for ch in dna]


# --------------------------------------------------------------------
# Claim 1: prefix-sum equivalence
# --------------------------------------------------------------------


def _independent_prefix_sum(data: bytes, reference_sequence: str) -> list:
    """
    Independently computes the expected output nucleotide-value sequence
    via a plain numpy-free running sum, WITHOUT calling dna_transform.
    """
    p_vals = _nucleotide_values(data)
    ref_vals = [NT_TO_VAL[ch] for ch in reference_sequence]
    rlen = len(ref_vals)

    out = []
    running = 0
    for i, p in enumerate(p_vals):
        running = (running + p + ref_vals[i % rlen]) % 4
        out.append(running)
    return out


def verify_prefix_sum_equivalence(reference_sequence: str, n_cases: int = 1000) -> bool:
    rng = random.Random(20260906)
    lengths = [0, 1] + [rng.randint(2, 5000) for _ in range(n_cases - 2)]

    all_match = True
    mismatches = []
    for idx, length in enumerate(lengths):
        data = bytes(rng.getrandbits(8) for _ in range(length))
        actual_output = dna_transform(data, reference_sequence)
        actual_vals = _nucleotide_values(actual_output)
        expected_vals = _independent_prefix_sum(data, reference_sequence)
        if actual_vals != expected_vals:
            all_match = False
            mismatches.append((idx, length))

    print(f"Claim 1 (prefix-sum equivalence): {n_cases} cases, lengths 0-5000 bytes "
          f"(including explicit length-0 and length-1 cases)")
    if all_match:
        print("  PASS: every case's dna_transform() output matched the independent prefix-sum computation exactly.")
    else:
        print(f"  FAIL: {len(mismatches)} / {n_cases} cases mismatched. First few: {mismatches[:5]}")
    return all_match


# --------------------------------------------------------------------
# Claim 2: avalanche closed form
# --------------------------------------------------------------------


def rerun_2000_trial_avalanche(reference_sequence: str):
    print("\nClaim 2a: re-running the 2,000-trial post_dna avalanche measurement "
          "(20 batches x 100 trials), matching scripts/measure_dna_transform_avalanche.py")

    def encrypt_dna_only(data: bytes) -> bytes:
        return dna_transform(data, reference_sequence)

    results = {}
    for filename in ("text_small.txt", "json_small.json", "random_small.bin"):
        data = _load_corpus_file(filename)
        batch_means = [
            avalanche_test(encrypt_dna_only, data, n_trials=100) for _ in range(20)
        ]
        mean = statistics.mean(batch_means)
        stdev = statistics.stdev(batch_means)
        results[filename] = (mean, stdev)
        print(f"  {filename:18s} mean={mean:.2f}% stdev={stdev:.2f}%")

    means = [m for m, _ in results.values()]
    in_range = all(30.4 <= m <= 31.8 for m in means)
    print(f"  {'PASS' if in_range else 'FAIL'}: all three means fall within the previously-reported 30.4-31.8% range"
          if in_range else
          f"  FAIL: not all means fall within 30.4-31.8% -- {results}")
    return in_range


def _hamming_bits(a: bytes, b: bytes) -> int:
    return sum(bin(x ^ y).count("1") for x, y in zip(a, b))


def verify_mechanism_and_decomposition(reference_sequence: str, n_trials: int = 500):
    """
    Claim 2b/2c: for many single-bit-flip trials on text_small.txt, verify
    (b) every nucleotide before the flip position is byte-identical between
        original and flipped post_dna output, and every nucleotide from the
        flip position onward differs from the original by the SAME constant
        (mod 4) throughout;
    (c) record, per trial, the downstream fraction (nucleotides at or after
        the flip position, as a fraction of the total) and the average bit
        -difference fraction among just those downstream nucleotides, to
        check the two claimed factors (~0.5, ~62.5%) separately.
    """
    print(f"\nClaim 2b/2c: mechanism + decomposition check, {n_trials} single-bit-flip trials "
          f"on text_small.txt")

    data = _load_corpus_file("text_small.txt")
    n_bits_total = len(data) * 8
    rng = random.Random(20260906)

    mechanism_violations = 0
    downstream_fractions = []
    downstream_bit_diff_fractions = []
    overall_bit_diff_fractions = []

    for _ in range(n_trials):
        bit_index = rng.randrange(n_bits_total)
        byte_index, bit_in_byte = divmod(bit_index, 8)
        flipped = bytearray(data)
        flipped[byte_index] ^= 1 << bit_in_byte
        flipped = bytes(flipped)

        original_out = dna_transform(data, reference_sequence)
        flipped_out = dna_transform(flipped, reference_sequence)

        original_vals = _nucleotide_values(original_out)
        flipped_vals = _nucleotide_values(flipped_out)
        n_nt = len(original_vals)

        # nucleotide index affected by this bit flip. avalanche_test's
        # bit_index uses `1 << bit_in_byte` (bit_in_byte=0 -> LSB), but
        # dna_codec.bytes_to_bits produces an MSB-first bit STRING
        # (f"{b:08b}") that bits_to_dna then groups into nucleotide pairs
        # from the string's start. The two numbering conventions are
        # mirrored within each byte, so bit_index must be converted to
        # the equivalent MSB-first string position before dividing by 2.
        string_bit_index = byte_index * 8 + (7 - bit_in_byte)
        flip_nt_index = string_bit_index // 2

        prefix_ok = original_vals[:flip_nt_index] == flipped_vals[:flip_nt_index]

        deltas = {
            (flipped_vals[i] - original_vals[i]) % 4
            for i in range(flip_nt_index, n_nt)
        }
        suffix_ok = len(deltas) == 1 and next(iter(deltas)) != 0

        if not (prefix_ok and suffix_ok):
            mechanism_violations += 1

        downstream_fraction = (n_nt - flip_nt_index) / n_nt
        downstream_fractions.append(downstream_fraction)

        # bit-difference fraction, restricted to downstream nucleotides only
        # (2 bits each), vs. overall (matching what avalanche_test reports).
        n_nt_bytes_total = len(original_out)
        overall_diff_bits = _hamming_bits(original_out, flipped_out)
        overall_bit_diff_fractions.append(100.0 * overall_diff_bits / (n_nt_bytes_total * 8))

        downstream_diff_bits = 0
        downstream_total_bits = 0
        for i in range(flip_nt_index, n_nt):
            byte_pos, offset = divmod(i, 4)
            if byte_pos >= len(original_out):
                continue
            # reconstruct this nucleotide's 2-bit value pair position within the byte
            orig_byte = original_out[byte_pos]
            flip_byte = flipped_out[byte_pos]
            shift = 6 - 2 * offset
            orig_pair = (orig_byte >> shift) & 0b11
            flip_pair = (flip_byte >> shift) & 0b11
            downstream_diff_bits += bin(orig_pair ^ flip_pair).count("1")
            downstream_total_bits += 2
        if downstream_total_bits > 0:
            downstream_bit_diff_fractions.append(100.0 * downstream_diff_bits / downstream_total_bits)

    print(f"  Mechanism violations: {mechanism_violations} / {n_trials} "
          f"(prefix unchanged AND suffix shifted by one constant nonzero delta)")
    print(f"  Downstream fraction: mean={statistics.mean(downstream_fractions):.4f} "
          f"(theory: ~0.5 for a uniformly random flip position)")
    print(f"  Downstream-only bit-diff fraction: mean={statistics.mean(downstream_bit_diff_fractions):.2f}% "
          f"(theory: ~62.5%)")
    print(f"  Overall avalanche (this trial set): mean={statistics.mean(overall_bit_diff_fractions):.2f}%")
    predicted = statistics.mean(downstream_fractions) * statistics.mean(downstream_bit_diff_fractions) / 100.0 * 100.0
    print(f"  Product of the two measured factors: {predicted:.2f}% "
          f"(closed-form prediction: 0.5 x 62.5% = 31.25%)")

    return mechanism_violations == 0


def run():
    reference_sequence = _load_reference_sequence()

    claim1_pass = verify_prefix_sum_equivalence(reference_sequence)
    claim2a_pass = rerun_2000_trial_avalanche(reference_sequence)
    claim2b_pass = verify_mechanism_and_decomposition(reference_sequence)

    print("\n=== Summary ===")
    print(f"Claim 1 (prefix-sum equivalence): {'PASS' if claim1_pass else 'FAIL'}")
    print(f"Claim 2a (2,000-trial avalanche reproduces 30.4-31.8%): {'PASS' if claim2a_pass else 'FAIL'}")
    print(f"Claim 2b (mechanism: unchanged prefix, constant-delta suffix): {'PASS' if claim2b_pass else 'FAIL'}")


if __name__ == "__main__":
    run()
