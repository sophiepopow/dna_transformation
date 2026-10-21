"""
src/classical_crypto.py

Classical-cipher layer for the DNA-encoding statistical impact study.

Wraps AES-256-GCM (pycryptodome) as the "classical encryption" stage used
by both experimental pipelines (see src/pipeline.py). AES-GCM is an
authenticated cipher: encryption produces a random nonce, the ciphertext,
and an authentication tag; decryption requires all three plus the key and
raises on tampering/corruption (wrong key, flipped bit, mismatched tag).
"""

from Crypto.Cipher import AES


def encrypt_aes_gcm(data: bytes, key: bytes) -> tuple[bytes, bytes, bytes]:
    """
    Encrypt `data` with AES-GCM under `key` (16 or 32 bytes).

    Returns (nonce, ciphertext, tag). A fresh random nonce is generated for
    every call (AES.new's default behaviour for MODE_GCM), so encrypting
    the same plaintext twice yields different ciphertext/nonce/tag triples.
    """
    cipher = AES.new(key, AES.MODE_GCM)
    ciphertext, tag = cipher.encrypt_and_digest(data)
    return cipher.nonce, ciphertext, tag


def decrypt_aes_gcm(nonce: bytes, ciphertext: bytes, tag: bytes, key: bytes) -> bytes:
    """
    Decrypt an AES-GCM (nonce, ciphertext, tag) triple produced by
    encrypt_aes_gcm, under the same `key`.

    Raises ValueError (via pycryptodome's verify step) if the tag does not
    match, i.e. the ciphertext or tag was corrupted or the wrong key was
    used.
    """
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    return cipher.decrypt_and_verify(ciphertext, tag)
