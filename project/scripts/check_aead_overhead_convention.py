"""
scripts/check_aead_overhead_convention.py

Follow-up to the M5 review finding (docs/reviews/M5_review.md, "Central
finding") that src/benchmark.py's size_overhead(), as exercised against
AES-GCM's ciphertext body alone, is mathematically guaranteed to return
exactly 0.0% for any real input -- AES-GCM is CTR-mode keystream XOR with
no block padding, so len(ciphertext) == len(plaintext) always. The real,
size-dependent overhead lives in the nonce and authentication tag, which
were being excluded.

This script does NOT change size_overhead() itself -- that function is a
correct, generic (new_size - old_size) / old_size calculator (verbatim
from the M5 spec). It only changes what bytes get passed to it, and
demonstrates the difference numerically using this project's actual
pycryptodome-based encrypt_aes_gcm().

Standard/convention this follows (checked against real sources before
implementing, not assumed):

1. Wikipedia, "Ciphertext expansion": ciphertext expansion is the length
   increase of a message when encrypted, explicitly citing the case where
   "the resulting ciphertext must include a message-unique Initialization
   Vector (IV)" as a standard cause of expansion -- i.e. the nonce/IV is
   conventionally counted as part of the expansion when it travels with
   the ciphertext.
   https://en.wikipedia.org/wiki/Ciphertext_expansion

2. RFC 5116, "An Interface and Algorithms for Authenticated Encryption":
   defines AEAD ciphertext expansion as the tag alone (an
   AEAD_AES_128_GCM ciphertext is exactly 16 octets longer than its
   plaintext) and explicitly does NOT fold the nonce into that figure --
   the nonce is treated as something the application communicates to the
   receiver by whatever means it chooses. Crucially, RFC 5116 explicitly
   permits (without requiring) counting the nonce alongside the
   ciphertext when it travels with it: "The nonce MAY be stored or
   transported with the ciphertext." (Earlier drafts of this script cited
   Go's crypto/cipher Overhead() as if returning "nonce + tag" were the
   general-purpose convention; checked again, Go's default AES-GCM
   Overhead() returns the 16-byte tag alone -- NonceSize() is separate.
   The 28-bytes-nonce-plus-tag figure exists only for a specific, narrower
   API, NewGCMWithRandomNonce, not for "standard AES-GCM." RFC 5116 is the
   correct citation for this project's choice, not Go's general Overhead().)
   https://www.rfc-editor.org/rfc/rfc5116.html

Applied to this project: src/pipeline.py's post_classical stage already
bundles {"nonce", "ciphertext", "tag"} together as what actually gets
"transmitted"/stored -- the nonce is not derived out-of-band here, so by
source 1 above (and RFC 5116's explicit allowance) it is reasonable to
count it toward size overhead, same as the tag, though RFC 5116 itself
formally defines "ciphertext expansion" as the tag alone.

Run from the `project/` directory:
    python3 scripts/check_aead_overhead_convention.py
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from classical_crypto import encrypt_aes_gcm
from benchmark import size_overhead

KEY = os.urandom(32)


def check(plaintext: bytes, label: str):
    nonce, ciphertext, tag = encrypt_aes_gcm(plaintext, KEY)

    body_only_pct = size_overhead(plaintext, ciphertext)
    full_aead_bytes = nonce + ciphertext + tag
    full_aead_pct = size_overhead(plaintext, full_aead_bytes)

    print(
        f"{label:22s} | plaintext={len(plaintext):7d}B  nonce={len(nonce)}B  tag={len(tag)}B  "
        f"ciphertext={len(ciphertext):7d}B | "
        f"body-only overhead={body_only_pct:8.4f}%  full-AEAD overhead={full_aead_pct:8.4f}%"
    )


if __name__ == "__main__":
    print("nonce/tag sizes are fixed per encryption; overhead % depends on plaintext size\n")
    check(b"x", "1 byte")
    check(b"x" * 16, "16 bytes")
    check(b"x" * 100, "100 bytes")
    check(os.urandom(10238), "10238 bytes (text_small)")
    check(os.urandom(204800), "204800 bytes (text_large)")
