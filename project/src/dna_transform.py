"""
src/dna_transform.py

DNA-domain transform layer for the DNA-encoding statistical impact study.

Design rationale (see project docs/findings.md / M1 revision notes for the
empirical justification):

- Combines the plaintext's DNA representation with a fixed reference DNA
  sequence via mod-4 addition over nucleotide values (A=0, T=1, C=2, G=3),
  which is the standard reversible "DNA addition" primitive used in
  lightweight DNA-cryptography literature (invertible via mod-4
  subtraction).

- Uses CHAINING (cipher-feedback style) instead of a static tiled mask or a
  single fixed-offset rotation: each output nucleotide depends on the
  entire preceding stream, not just its position modulo the reference
  sequence's length.

- Does NOT use a cryptographic hash function (e.g. SHA-256) to derive a
  mask. A cryptographically strong keystream pushes ALL input entropy
  classes toward the same near-maximal output entropy regardless of input
  structure, erasing the entropy-class signal this study measures.

Empirical validation (4000-byte samples, 64-nt reference sequence):
    Design                  H(text)  H(random)  ciphertext-only
                                                  autocorr @ lag=16
    ---------------------------------------------------------------
    SHA-256 mask + XOR       7.957     7.957      0.011 / 0.002
      -> erases the entropy-class signal entirely (bad: too strong)
    Tiled mask + fixed rot   6.805     7.951      0.835 / -0.008
      -> severe periodicity leak on structured data (bad: too weak,
         detectable without knowing the plaintext)
    Chained mod-4 (this)     7.272     7.953      0.017 / 0.018
      -> measurable entropy gap preserved (text/JSON below random),
         periodicity leak resolved (near chance-level autocorrelation)

Round-trip correctness (this module's core requirement) is fully
preserved: dna_inverse_transform is an exact inverse of dna_transform for
any reference_sequence and any byte string, including b"".
"""

from dna_codec import bytes_to_bits, bits_to_dna, dna_to_bits, bits_to_bytes

DEFAULT_MAPPING = {"00": "A", "01": "T", "10": "C", "11": "G"}


def _mapping_to_value_table(mapping: dict):
    """
    Derive nucleotide<->integer-value tables directly from the active
    2-bit mapping, so the mod-4 arithmetic stays correct even if a
    non-default mapping is passed in.
    """
    nt_to_val = {nt: int(bits, 2) for bits, nt in mapping.items()}
    val_to_nt = {v: nt for nt, v in nt_to_val.items()}
    return nt_to_val, val_to_nt


def _validate_reference_sequence(reference_sequence: str) -> str:
    reference_sequence = reference_sequence.strip().upper()
    if not reference_sequence or any(ch not in "ATCG" for ch in reference_sequence):
        raise ValueError(
            "reference_sequence must be non-empty and contain only A, T, C, G"
        )
    return reference_sequence


def dna_transform(data: bytes, reference_sequence: str, mapping: dict = None) -> bytes:
    """
    Apply the chained DNA-domain mod-4 transform to `data`.

    For each nucleotide position i in the DNA representation of `data`:
        c[i] = (plain[i] + ref[i mod len(ref)] + c[i-1]) mod 4
    with c[-1] = 0 (fixed IV).

    Deterministic and fully invertible via dna_inverse_transform, given
    the same reference_sequence and mapping.

    Raises ValueError if reference_sequence is empty or contains
    characters other than A, T, C, G.
    """
    if not data:
        return b""

    mapping = mapping or DEFAULT_MAPPING
    reference_sequence = _validate_reference_sequence(reference_sequence)
    nt_to_val, val_to_nt = _mapping_to_value_table(mapping)

    plain_dna = bits_to_dna(bytes_to_bits(data), mapping)
    plain_vals = [nt_to_val[ch] for ch in plain_dna]
    ref_vals = [nt_to_val[ch] for ch in reference_sequence]
    rlen = len(ref_vals)

    out_vals = []
    prev = 0
    for i, p in enumerate(plain_vals):
        r = ref_vals[i % rlen]
        c = (p + r + prev) % 4
        out_vals.append(c)
        prev = c

    cipher_dna = "".join(val_to_nt[v] for v in out_vals)
    cipher_bits = dna_to_bits(cipher_dna, mapping)
    return bits_to_bytes(cipher_bits)


def dna_inverse_transform(data: bytes, reference_sequence: str, mapping: dict = None) -> bytes:
    """
    Exact inverse of dna_transform. Given ciphertext bytes produced by
    dna_transform and the same reference_sequence/mapping, recovers the
    original plaintext bytes exactly.
    """
    if not data:
        return b""

    mapping = mapping or DEFAULT_MAPPING
    reference_sequence = _validate_reference_sequence(reference_sequence)
    nt_to_val, val_to_nt = _mapping_to_value_table(mapping)

    cipher_dna = bits_to_dna(bytes_to_bits(data), mapping)
    cipher_vals = [nt_to_val[ch] for ch in cipher_dna]
    ref_vals = [nt_to_val[ch] for ch in reference_sequence]
    rlen = len(ref_vals)

    out_vals = []
    prev = 0
    for i, c in enumerate(cipher_vals):
        r = ref_vals[i % rlen]
        p = (c - r - prev) % 4
        out_vals.append(p)
        prev = c  # feedback uses the CIPHERTEXT nucleotide, always known at decrypt time

    plain_dna = "".join(val_to_nt[v] for v in out_vals)
    plain_bits = dna_to_bits(plain_dna, mapping)
    return bits_to_bytes(plain_bits)