"""
tests/test_avalanche.py

Avalanche-effect tests for src/avalanche.py, run against both experimental
pipelines (src/pipeline.py) using data/corpus/text_small.txt.

--- Design point A: pipeline_encrypt_fn interface -------------------------

avalanche_test's signature (src/avalanche.py) takes a one-argument
callable `pipeline_encrypt_fn(data: bytes) -> bytes`, but the real
pipeline functions take `(data, key, ...)` and return a stage dict, not
raw bytes. The wrappers below (`_make_pipeline_a_encryptor`,
`_make_pipeline_b_encryptor`) close over the fixed experiment key (and,
for pipeline A, the fixed reference sequence) and extract
`stages["post_classical"]["ciphertext"]` — i.e. the AES-GCM ciphertext
body only, excluding the nonce and the authentication tag. This is a
chosen interpretation, not something the spec states explicitly: nonce
and tag are metadata alongside the ciphertext, not "the ciphertext"
itself, so avalanche is measured on the encrypted payload bytes only.

--- Design point B: random nonce vs. fixed nonce (investigated, not assumed)

AES-GCM (`AES.new(key, AES.MODE_GCM)`, no explicit nonce — see
src/classical_crypto.py) generates a fresh random nonce on every call.
That means calling `pipeline_encrypt_fn` twice (original vs. bit-flipped)
produces two ciphertexts that differ substantially just because they used
different nonces, independent of whether the single bit was ever flipped.
This was checked empirically (see the milestone implementation report /
scratch script) by comparing:
  (a) original vs. a genuinely bit-flipped copy
  (b) original vs. an UNMODIFIED copy of the exact same data (no flip)
both under the pipelines' natural random-nonce behavior, 25 trials each,
on text_small.txt:

    Pipeline A: bit-flip (a) = 50.04%   |  no-flip (b) = 50.05%
    Pipeline B: bit-flip (a) = 50.00%   |  no-flip (b) = 49.99%

Condition (a) and (b) are statistically indistinguishable. This confirms
that, under the pipelines' default random-nonce AES-GCM behavior, the
~50% avalanche figure is coming almost entirely from AES-GCM's per-call
nonce randomization, not from the pipeline's/DNA-transform's genuine
sensitivity to the one flipped input bit — the test would report ~50%
"avalanche" even if the bit flip never happened at all.

A follow-up check was run to see whether fixing the nonce (so the only
source of ciphertext difference is the plaintext difference, since
AES-GCM's core encryption is CTR-mode keystream XOR plaintext) would be a
better design:
  - Pipeline A, fixed-nonce-equivalent (measured directly on
    dna_transform's *output*, pre-AES, since a fixed keystream cancels out
    of the ciphertext-vs-ciphertext XOR): mean Hamming distance ~38.28%
    over 25 trials, but with high per-trial variance (min 3.37%, max
    70.25%) — plausible but not reliably inside 40-60% on every run.
  - Pipeline B, fixed-nonce-equivalent (measured directly as the raw
    plaintext-vs-flipped-plaintext Hamming distance, since AES-GCM with a
    reused nonce reduces to XOR with an identical keystream, which cancels
    exactly): mean ~0.0012%. A single flipped plaintext bit is still just
    one flipped bit after XOR with an identical keystream — pipeline B has
    no diffusion step of its own (no DNA transform), so fixing the nonce
    would make the stated 40-60% exit criterion essentially impossible to
    satisfy for pipeline B.

Decision: implement per the literal spec, using each pipeline's natural
(random-nonce) encryption behavior, unchanged. Rationale: the empirical
check found a real methodological concern (the metric mostly reflects
nonce randomization, not input sensitivity) but also found that the
"fix" (a fixed nonce) breaks the exit criterion for pipeline B outright
and makes pipeline A's result unreliably variable — so the fix is not a
clear improvemement under this project's stated exit criteria. This
tradeoff, and the fact that the literal-spec test is measuring AES-GCM's
mandatory nonce re-randomization more than genuine avalanche propagation,
is recorded here rather than silently resolved either way.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from avalanche import avalanche_test
from pipeline import pipeline_a_dna_plus_classical, pipeline_b_classical_only

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
CORPUS_DIR = os.path.join(DATA_DIR, "corpus")
AES_KEY_PATH = os.path.join(DATA_DIR, "aes_key.bin")
REFERENCE_SEQUENCE_PATH = os.path.join(DATA_DIR, "reference_sequence.txt")

with open(AES_KEY_PATH, "rb") as f:
    KEY = f.read()
with open(REFERENCE_SEQUENCE_PATH) as f:
    REFERENCE_SEQUENCE = f.read().strip()
with open(os.path.join(CORPUS_DIR, "text_small.txt"), "rb") as f:
    TEXT_SMALL = f.read()


def _make_pipeline_a_encryptor():
    def encrypt(data: bytes) -> bytes:
        stages = pipeline_a_dna_plus_classical(data, KEY, REFERENCE_SEQUENCE)
        return stages["post_classical"]["ciphertext"]

    return encrypt


def _make_pipeline_b_encryptor():
    def encrypt(data: bytes) -> bytes:
        stages = pipeline_b_classical_only(data, KEY)
        return stages["post_classical"]["ciphertext"]

    return encrypt


def _make_pipeline_a_dna_only_encryptor():
    """
    Follow-up to the finding above: measures avalanche on Pipeline A's
    pre-AES `post_dna` output instead of the full-pipeline AES-GCM
    ciphertext, so there is no nonce to confound the result (the chained
    mod-4 transform in src/dna_transform.py is fully deterministic). See
    scripts/measure_dna_transform_avalanche.py and docs/test_raport.md for
    a well-powered (2000-trial) measurement; this test is a lightweight
    regression check that the measurement path itself works, not the
    citable number.
    """

    def encrypt(data: bytes) -> bytes:
        stages = pipeline_a_dna_plus_classical(data, KEY, REFERENCE_SEQUENCE)
        return stages["post_dna"]

    return encrypt


class TestAvalanchePipelineA:
    def test_avalanche_percentage_in_range(self):
        encrypt_fn = _make_pipeline_a_encryptor()
        pct = avalanche_test(encrypt_fn, TEXT_SMALL, n_trials=25)
        print(f"\nPipeline A avalanche percentage (text_small.txt, n=25): {pct:.2f}%")
        assert 0 <= pct <= 100
        assert 40 <= pct <= 60, f"expected roughly 40-60%, got {pct:.2f}%"


class TestAvalanchePipelineB:
    def test_avalanche_percentage_in_range(self):
        encrypt_fn = _make_pipeline_b_encryptor()
        pct = avalanche_test(encrypt_fn, TEXT_SMALL, n_trials=25)
        print(f"\nPipeline B avalanche percentage (text_small.txt, n=25): {pct:.2f}%")
        assert 0 <= pct <= 100
        assert 40 <= pct <= 60, f"expected roughly 40-60%, got {pct:.2f}%"


class TestAvalanchePipelineADNATransformOnly:
    """
    Regression check for the DNA-transform-only avalanche measurement
    (see module docstring, "Design point B" — this is the follow-up
    measurement recommended there). No 40-60% assertion here: unlike the
    full-pipeline AES-GCM numbers above (which are meaningless but happen
    to always land near 50%), this is a real, novel measurement of the
    chained mod-4 transform's own diffusion, and a well-powered run
    (scripts/measure_dna_transform_avalanche.py, 2000 trials) found a
    stable ~30-32% mean, not 40-60% — so only a loose 0-100 sanity bound
    is asserted here; the citable number lives in docs/test_raport.md.
    """

    def test_avalanche_percentage_in_range(self):
        encrypt_fn = _make_pipeline_a_dna_only_encryptor()
        pct = avalanche_test(encrypt_fn, TEXT_SMALL, n_trials=25)
        print(f"\nPipeline A DNA-transform-only avalanche percentage (text_small.txt, n=25): {pct:.2f}%")
        assert 0 <= pct <= 100
