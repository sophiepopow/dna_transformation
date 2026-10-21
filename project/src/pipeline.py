"""
src/pipeline.py

Composes the two experimental pipelines compared throughout this thesis:

- Pipeline A (`pipeline_a_dna_plus_classical`): DNA-domain transform
  (src/dna_transform.py) followed by AES-GCM (src/classical_crypto.py).
- Pipeline B (`pipeline_b_classical_only`): AES-GCM only, no DNA-domain
  transform. This is the control pipeline the thesis compares Pipeline A
  against.

Each pipeline function returns a dict exposing every intermediate stage
(`input`, optionally `post_dna`, `post_classical`) so later milestones
(M4 statistical metrics, M5 benchmarking) can measure entropy /
chi-square / compression / correlation at each stage independently.

Signature note (deviation from the milestone plan's literal text): M1's
final `dna_transform` / `dna_inverse_transform` signature takes
`reference_sequence: str` (a string of A/T/C/G characters that the
transform combines with the plaintext via chained mod-4 addition), not a
precomputed `mask: bytes` as the original M1 spec assumed before its
revision (see docs/milestone_plan.md's "M1 Revision" addendum). M2's plan
text still says `pipeline_a_dna_plus_classical(data, key, mask)`; this
module names that third parameter `reference_sequence` to match M1's
actual, already-implemented signature rather than silently reintroducing
a `mask: bytes` parameter that no longer corresponds to anything real in
the codebase.

AES-GCM nonce/tag handling: `encrypt_aes_gcm` returns a fresh
(nonce, ciphertext, tag) triple on every call, and `decrypt_aes_gcm` needs
all three plus the key to invert it. Both pipelines carry the triple as a
dict under the `post_classical` stage key, e.g.
`{"nonce": ..., "ciphertext": ..., "tag": ...}`, so the full pipeline
result dict is self-contained and sufficient (together with the key, and
for Pipeline A the reference_sequence) to reconstruct the original input.
"""

from classical_crypto import encrypt_aes_gcm, decrypt_aes_gcm
from dna_transform import dna_transform, dna_inverse_transform


def pipeline_b_classical_only(data: bytes, key: bytes) -> dict:
    """
    Pipeline B (control): AES-GCM only, no DNA-domain transform.

    Returns {"input": data, "post_classical": {"nonce", "ciphertext", "tag"}}.
    """
    nonce, ciphertext, tag = encrypt_aes_gcm(data, key)
    return {
        "input": data,
        "post_classical": {"nonce": nonce, "ciphertext": ciphertext, "tag": tag},
    }


def pipeline_a_dna_plus_classical(data: bytes, key: bytes, reference_sequence: str) -> dict:
    """
    Pipeline A: DNA-domain transform (src/dna_transform.py), then AES-GCM.

    `reference_sequence` is a string of A/T/C/G nucleotides (see M1's
    dna_transform for its role in the chained mod-4 transform) — this is
    the M1-signature-accurate name for what the milestone plan's literal
    text calls `mask`.

    Returns {"input": data, "post_dna": ..., "post_classical": {"nonce", "ciphertext", "tag"}}.
    """
    post_dna = dna_transform(data, reference_sequence)
    nonce, ciphertext, tag = encrypt_aes_gcm(post_dna, key)
    return {
        "input": data,
        "post_dna": post_dna,
        "post_classical": {"nonce": nonce, "ciphertext": ciphertext, "tag": tag},
    }


def decrypt_pipeline_b(stages: dict, key: bytes) -> bytes:
    """
    Exact inverse of pipeline_b_classical_only: AES-GCM decrypt only.
    """
    post_classical = stages["post_classical"]
    return decrypt_aes_gcm(
        post_classical["nonce"], post_classical["ciphertext"], post_classical["tag"], key
    )


def decrypt_pipeline_a(stages: dict, key: bytes, reference_sequence: str) -> bytes:
    """
    Exact inverse of pipeline_a_dna_plus_classical: AES-GCM decrypt, then
    the DNA-domain inverse transform. `reference_sequence` must match the
    one used to produce `stages`.
    """
    post_classical = stages["post_classical"]
    post_dna = decrypt_aes_gcm(
        post_classical["nonce"], post_classical["ciphertext"], post_classical["tag"], key
    )
    return dna_inverse_transform(post_dna, reference_sequence)
