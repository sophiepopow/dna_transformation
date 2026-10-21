"""
tests/test_dna_transform.py

Round-trip and regression tests for the chained DNA-domain mod-4 transform
in src/dna_transform.py.

Background: an earlier version derived its mask via SHA-256 hashing
(cryptographically strong -> erased the entropy-class signal the study
measures), and a naive tiled-mask + fixed-rotation version left a severe
periodicity artifact (ciphertext-only autocorrelation ~0.83 at
lag = reference-sequence length in bytes, on structured text). The
chained mod-4 design fixes both. TestNoPeriodicityLeak below is a
regression guard against reintroducing the periodicity bug.
"""

import os
import random
import sys

sys.path.insert(0, "src")

import pytest
from dna_transform import dna_transform, dna_inverse_transform

REFERENCE_SEQUENCE = "AACTTTAAGAAATTATGTGCATGCCTTCAAGACCCAGAGACCTAATCATAGCGCTCCTCATTTG"  # 64 nt, fixed


def _random_byte_strings(n=100, min_len=1, max_len=10_000, seed=1234):
    rng = random.Random(seed)
    for _ in range(n):
        length = rng.randint(min_len, max_len)
        yield bytes(rng.getrandbits(8) for _ in range(length))


class TestRoundTrip:
    def test_round_trip_random_lengths(self):
        for data in _random_byte_strings():
            transformed = dna_transform(data, REFERENCE_SEQUENCE)
            recovered = dna_inverse_transform(transformed, REFERENCE_SEQUENCE)
            assert recovered == data

    def test_round_trip_empty_input(self):
        assert dna_transform(b"", REFERENCE_SEQUENCE) == b""
        assert dna_inverse_transform(b"", REFERENCE_SEQUENCE) == b""

    def test_round_trip_every_single_byte_value(self):
        for value in range(256):
            data = bytes([value])
            transformed = dna_transform(data, REFERENCE_SEQUENCE)
            assert dna_inverse_transform(transformed, REFERENCE_SEQUENCE) == data

    def test_round_trip_text_and_binary_samples(self):
        text_sample = ("the quick brown fox jumps over the lazy dog " * 20).encode("utf-8")
        binary_sample = os.urandom(5000)
        for sample in (text_sample, binary_sample):
            transformed = dna_transform(sample, REFERENCE_SEQUENCE)
            assert dna_inverse_transform(transformed, REFERENCE_SEQUENCE) == sample


class TestDeterminism:
    def test_same_input_same_reference_gives_same_output(self):
        data = os.urandom(500)
        assert dna_transform(data, REFERENCE_SEQUENCE) == dna_transform(data, REFERENCE_SEQUENCE)

    def test_different_reference_gives_different_output(self):
        data = os.urandom(500)
        other_reference = "TTTTGGGGCCCCAAAATTTTGGGGCCCCAAAATTTTGGGGCCCCAAAATTTTGGGGCCCCAAAA"
        assert dna_transform(data, REFERENCE_SEQUENCE) != dna_transform(data, other_reference)


class TestValidation:
    def test_empty_reference_sequence_raises(self):
        with pytest.raises(ValueError):
            dna_transform(b"some data", "")

    def test_invalid_characters_in_reference_sequence_raises(self):
        with pytest.raises(ValueError):
            dna_transform(b"some data", "ATCGXYZ")


class TestNoPeriodicityLeak:
    """
    Regression guard: ciphertext must NOT preserve the plaintext's
    lag-`period` XOR relationship the way the old tiled-mask design did.
    period = len(REFERENCE_SEQUENCE) in bytes (64 nt -> 16 bytes, since
    4 nucleotides = 1 byte at 2 bits/nucleotide).
    """

    def test_no_periodicity_leak_on_structured_text(self):
        period_bytes = len(REFERENCE_SEQUENCE) // 4
        text = (
            "the quick brown fox jumps over the lazy dog and then the dog "
            "barks at the fox while the sun sets over the quiet hill " * 40
        ).encode("ascii")[:4000]
        cipher = dna_transform(text, REFERENCE_SEQUENCE)

        n_check = len(text) - period_bytes
        preserved = sum(
            1
            for i in range(n_check)
            if (cipher[i] ^ cipher[i + period_bytes]) == (text[i] ^ text[i + period_bytes])
        )
        preserved_ratio = preserved / n_check
        # Old (buggy) tiled-mask design: this ratio was 1.0 (always preserved).
        # Chance level for unrelated bytes matching on XOR is ~1/256 (~0.004).
        # 0.05 gives a generous margin above chance while still failing hard
        # on the old bug.
        assert preserved_ratio < 0.05, (
            f"periodicity leak detected: {preserved_ratio:.3f} of lag-{period_bytes} "
            "byte pairs preserved their XOR relationship (expected near-chance level)"
        )