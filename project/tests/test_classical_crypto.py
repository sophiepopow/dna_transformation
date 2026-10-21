"""
tests/test_classical_crypto.py

Tests for the AES-GCM wrapper in src/classical_crypto.py.

Added after the M2 independent review flagged that tamper-detection and
nonce-freshness had only been checked manually (see docs/reviews/M2_review.md
and docs/test_raport.md) and were not covered by the committed test suite.
Both properties matter beyond style: a reused/deterministic GCM nonce under
a fixed key (this project's data/aes_key.bin is fixed and reused across all
experiments) would be a real cryptographic break, and a decrypt() that
silently accepted tampered input would corrupt every downstream statistical
measurement without ever failing a round-trip test.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import pytest
from classical_crypto import encrypt_aes_gcm, decrypt_aes_gcm

KEY = os.urandom(32)


class TestRoundTrip:
    def test_round_trip(self):
        data = b"the quick brown fox jumps over the lazy dog"
        nonce, ciphertext, tag = encrypt_aes_gcm(data, KEY)
        assert decrypt_aes_gcm(nonce, ciphertext, tag, KEY) == data

    def test_round_trip_empty_input(self):
        nonce, ciphertext, tag = encrypt_aes_gcm(b"", KEY)
        assert decrypt_aes_gcm(nonce, ciphertext, tag, KEY) == b""


class TestNonceFreshness:
    def test_nonce_is_unique_per_call(self):
        data = b"identical plaintext encrypted many times"
        nonces = set()
        ciphertexts = set()
        for _ in range(200):
            nonce, ciphertext, _ = encrypt_aes_gcm(data, KEY)
            nonces.add(nonce)
            ciphertexts.add(ciphertext)
        assert len(nonces) == 200, "nonce reuse detected under a fixed key"
        assert len(ciphertexts) == 200


class TestTamperDetection:
    def test_wrong_key_raises(self):
        data = b"some sensitive plaintext"
        nonce, ciphertext, tag = encrypt_aes_gcm(data, KEY)
        wrong_key = os.urandom(32)
        with pytest.raises(ValueError):
            decrypt_aes_gcm(nonce, ciphertext, tag, wrong_key)

    def test_corrupted_ciphertext_raises(self):
        data = b"some sensitive plaintext"
        nonce, ciphertext, tag = encrypt_aes_gcm(data, KEY)
        corrupted = bytes([ciphertext[0] ^ 0x01]) + ciphertext[1:]
        with pytest.raises(ValueError):
            decrypt_aes_gcm(nonce, corrupted, tag, KEY)

    def test_corrupted_tag_raises(self):
        data = b"some sensitive plaintext"
        nonce, ciphertext, tag = encrypt_aes_gcm(data, KEY)
        corrupted_tag = bytes([tag[0] ^ 0x01]) + tag[1:]
        with pytest.raises(ValueError):
            decrypt_aes_gcm(nonce, ciphertext, corrupted_tag, KEY)
