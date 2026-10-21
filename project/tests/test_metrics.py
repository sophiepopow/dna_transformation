"""
tests/test_metrics.py

Unit tests for src/metrics.py: shannon_entropy, chi_square_uniform,
compression_ratio, pearson_correlation.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from metrics import (
    shannon_entropy,
    chi_square_uniform,
    compression_ratio,
    pearson_correlation,
)

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
CORPUS_DIR = os.path.join(DATA_DIR, "corpus")

CORPUS_FILES = [
    "text_small.txt",
    "text_large.txt",
    "json_small.json",
    "json_large.json",
    "random_small.bin",
    "random_large.bin",
]


def _load_corpus_file(name: str) -> bytes:
    with open(os.path.join(CORPUS_DIR, name), "rb") as f:
        return f.read()


class TestShannonEntropy:
    def test_random_data_high_entropy(self):
        assert shannon_entropy(os.urandom(10000)) > 7.9

    def test_constant_byte_low_entropy(self):
        assert shannon_entropy(b"a" * 10000) < 0.1

    def test_empty_data(self):
        assert shannon_entropy(b"") == 0.0

    def test_two_symbols_entropy_is_one(self):
        # Exactly two byte values, equal frequency -> exactly 1.0 bit/byte.
        data = (b"\x00\x01") * 5000
        assert abs(shannon_entropy(data) - 1.0) < 1e-9


class TestChiSquareUniform:
    def test_uniform_bytes_low_chi_square(self):
        # All 256 byte values equally represented -> statistic should be
        # exactly 0 (perfect match to the uniform expectation).
        data = bytes(range(256)) * 40
        assert chi_square_uniform(data) < 1e-6

    def test_constant_byte_high_chi_square(self):
        # A single repeated byte value is maximally non-uniform -> large
        # chi-square statistic relative to the uniform-bytes case.
        uniform_stat = chi_square_uniform(bytes(range(256)) * 40)
        skewed_stat = chi_square_uniform(b"a" * 10240)
        assert skewed_stat > uniform_stat

    def test_empty_data(self):
        assert chi_square_uniform(b"") == 0.0


class TestCompressionRatio:
    def test_all_corpus_files_finite_float(self):
        for name in CORPUS_FILES:
            data = _load_corpus_file(name)
            ratio = compression_ratio(data)
            assert isinstance(ratio, float)
            assert ratio == ratio  # not NaN
            assert ratio not in (float("inf"), float("-inf"))

    def test_repetitive_data_compresses_well(self):
        data = b"abcdefgh" * 5000
        assert compression_ratio(data) < 0.5

    def test_random_data_does_not_compress_well(self):
        data = os.urandom(10000)
        # gzip framing overhead means the ratio can exceed 1.0 for
        # incompressible data; either way it should be nowhere near the
        # repetitive-data ratio.
        assert compression_ratio(data) > 0.9

    def test_empty_data(self):
        assert compression_ratio(b"") == 0.0


class TestPearsonCorrelation:
    def test_identical_data_correlates_perfectly(self):
        data = os.urandom(5000)
        assert abs(pearson_correlation(data, data) - 1.0) < 1e-9

    def test_truncates_to_shorter_length(self):
        data = os.urandom(5000)
        # Same bytes, just a shorter second copy -> still perfect
        # correlation over the truncated overlap.
        assert abs(pearson_correlation(data, data[:2000]) - 1.0) < 1e-9

    def test_empty_input_returns_zero(self):
        assert pearson_correlation(b"", b"abc") == 0.0

    def test_constant_input_returns_zero(self):
        # Zero-variance input would make numpy corrcoef return NaN;
        # this should be handled and return 0.0 instead.
        assert pearson_correlation(b"a" * 100, os.urandom(100)) == 0.0
