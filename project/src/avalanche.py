"""
src/avalanche.py

Avalanche-effect test for the DNA-encoding statistical impact study.
Methodological template: *INRU: A Quasigroup Based Lightweight Block
Cipher* (https://arxiv.org/pdf/2112.07411) — flip one bit per trial across
many random inputs, then measure the Hamming-distance percentage between
ciphertexts. A cryptographically sound cipher is expected to land close to
50% (an ideal avalanche effect: flipping one input bit flips roughly half
of the output bits).

`pipeline_encrypt_fn` interface (design point A — documented, not silently
picked): the M4 spec's signature is a single-argument callable
`pipeline_encrypt_fn(data) -> ciphertext_bytes`, but this project's actual
pipeline functions (src/pipeline.py) take `(data, key, ...)` and return a
stage dict, not raw bytes. The interpretation used here, applied by the
caller (tests/test_avalanche.py) via a closure: `pipeline_encrypt_fn` is a
one-argument wrapper that fixes the key (and reference_sequence for
pipeline A) and returns only the `post_classical["ciphertext"]` bytes from
the pipeline's result dict — i.e. the AES-GCM ciphertext body, excluding
the nonce and the authentication tag. Ciphertext body only (not nonce/tag)
was chosen because nonce/tag are not "the ciphertext" in the usual sense
and mixing them in would conflate authentication-tag bits (a MAC over the
ciphertext, not itself an avalanche signal in the same sense) and (for
random-nonce mode) nonce bits that are independent of the plaintext by
construction, with the actual encrypted payload.
"""

import random


def avalanche_test(pipeline_encrypt_fn, data: bytes, n_trials: int = 25) -> float:
    """
    Avalanche-effect test: for each of `n_trials` trials, flip one random
    bit in a fresh copy of `data`, run `pipeline_encrypt_fn` on both the
    unmodified original and the bit-flipped copy, and compute the Hamming
    distance between the two resulting ciphertexts as a percentage of
    total ciphertext bits. Returns the mean percentage across all trials.

    `pipeline_encrypt_fn` must be a one-argument callable
    `pipeline_encrypt_fn(data: bytes) -> bytes` returning ciphertext bytes
    for the given input (see this module's docstring for how the two
    project pipelines are wrapped to satisfy this interface).

    Raises ValueError if `data` is empty (there is no bit to flip).
    """
    if not data:
        raise ValueError("avalanche_test requires non-empty data (no bit to flip)")

    percentages = []
    for _ in range(n_trials):
        flipped = bytearray(data)
        bit_index = random.randrange(len(data) * 8)
        byte_index, bit_in_byte = divmod(bit_index, 8)
        flipped[byte_index] ^= 1 << bit_in_byte
        flipped = bytes(flipped)

        ciphertext_original = pipeline_encrypt_fn(data)
        ciphertext_flipped = pipeline_encrypt_fn(flipped)

        n_bits = min(len(ciphertext_original), len(ciphertext_flipped)) * 8
        hamming_distance = _hamming_distance_bits(
            ciphertext_original[: n_bits // 8], ciphertext_flipped[: n_bits // 8]
        )
        percentages.append(100.0 * hamming_distance / n_bits)

    return sum(percentages) / len(percentages)


def _hamming_distance_bits(a: bytes, b: bytes) -> int:
    """Number of differing bits between equal-length byte strings a and b."""
    return sum(bin(x ^ y).count("1") for x, y in zip(a, b))
