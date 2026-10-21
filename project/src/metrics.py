"""
src/metrics.py

Statistical metrics module for the DNA-encoding statistical impact study.
This is the project's real, formal metrics module (intended to be reused
as-is by the M6 full experimental run) — every function here is a fresh
implementation per the M4 spec, independent of the stdlib-only
`shannon_entropy` already used for the M1 revision's periodicity check in
`scripts/measure_entropy_periodicity.py`. That script's version stays as
historical evidence for the M1 design decision; this module is the one
later milestones should import.

Functions:
- shannon_entropy(data)      -> bits/byte, via a 256-bin numpy histogram
                                 over byte values.
- chi_square_uniform(data)   -> chi-square statistic against a uniform
                                 256-bin expectation (scipy.stats.chisquare).
- compression_ratio(data)    -> len(gzip.compress(data)) / len(data).
- pearson_correlation(a, b)  -> numpy corrcoef on byte arrays truncated to
                                 equal length.
"""

import gzip

import numpy as np
from scipy.stats import chisquare


def shannon_entropy(data: bytes) -> float:
    """
    Shannon entropy of `data` in bits/byte, computed from a 256-bin numpy
    histogram over byte values (0-255).

    Returns 0.0 for empty input (no information content).
    """
    if not data:
        return 0.0

    counts, _ = np.histogram(
        np.frombuffer(data, dtype=np.uint8), bins=256, range=(0, 256)
    )
    counts = counts[counts > 0]
    probabilities = counts / counts.sum()
    return float(-np.sum(probabilities * np.log2(probabilities)))


def chi_square_uniform(data: bytes) -> float:
    """
    Chi-square goodness-of-fit statistic testing whether the byte-value
    distribution of `data` matches a uniform distribution over all 256
    possible byte values, via scipy.stats.chisquare.

    A larger statistic indicates a larger departure from uniformity
    (structured/low-entropy data is expected to score higher than
    near-random data).
    """
    if not data:
        return 0.0

    observed, _ = np.histogram(
        np.frombuffer(data, dtype=np.uint8), bins=256, range=(0, 256)
    )
    expected = np.full(256, len(data) / 256.0)
    statistic, _ = chisquare(f_obs=observed, f_exp=expected)
    return float(statistic)


def compression_ratio(data: bytes) -> float:
    """
    Ratio of gzip-compressed size to original size:
    len(gzip.compress(data)) / len(data).

    Lower ratios indicate more redundancy (compresses well); ratios near
    or above 1.0 indicate near-incompressible (high-entropy/random) data.
    """
    if not data:
        return 0.0
    return len(gzip.compress(data)) / len(data)


def pearson_correlation(a: bytes, b: bytes) -> float:
    """
    Pearson correlation coefficient between the byte values of `a` and
    `b`, truncated to the length of the shorter of the two, via numpy
    corrcoef.

    Returns 0.0 if either input is empty after truncation, or if either
    array has zero variance (corrcoef would otherwise return NaN).
    """
    n = min(len(a), len(b))
    if n == 0:
        return 0.0

    arr_a = np.frombuffer(a[:n], dtype=np.uint8).astype(np.float64)
    arr_b = np.frombuffer(b[:n], dtype=np.uint8).astype(np.float64)

    if arr_a.std() == 0 or arr_b.std() == 0:
        return 0.0

    corr_matrix = np.corrcoef(arr_a, arr_b)
    return float(corr_matrix[0, 1])
