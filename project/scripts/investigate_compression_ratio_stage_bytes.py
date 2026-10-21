"""
scripts/investigate_compression_ratio_stage_bytes.py

Read-only diagnostic: which byte string is compression_ratio() actually
computed on at each pipeline stage -- the AES-GCM ciphertext body alone,
or the concatenated nonce+ciphertext+tag (full_aead_bytes)?

Does not modify src/metrics.py, src/pipeline.py, or any measurement
script. Only imports and calls them exactly as scripts/run_experiment.py
and scripts/measure_post_classical_repeated.py already do, and prints the
gzip input/output lengths directly for text_small.txt at post_classical.

Run from the `project/` directory:
    python3 scripts/investigate_compression_ratio_stage_bytes.py
"""

import gzip
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from metrics import compression_ratio  # noqa: E402
from pipeline import pipeline_a_dna_plus_classical  # noqa: E402

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
CORPUS_DIR = os.path.join(DATA_DIR, "corpus")


def _load_key() -> bytes:
    with open(os.path.join(DATA_DIR, "aes_key.bin"), "rb") as f:
        return f.read()


def _load_reference_sequence() -> str:
    with open(os.path.join(DATA_DIR, "reference_sequence.txt")) as f:
        return f.read().strip()


def run():
    print("=== Where compression_ratio() is actually called, per grep of the real scripts ===")
    print('scripts/run_experiment.py:334:    comp_ratio = compression_ratio(stage_bytes)')
    print('  where stage_bytes = _stage_metric_bytes(stage, stages), and for stage=="post_classical"')
    print('  that function (scripts/run_experiment.py, _stage_metric_bytes) returns')
    print('  stages["post_classical"]["ciphertext"] -- the ciphertext BODY ALONE,')
    print('  explicitly excluding nonce and tag (see that function\'s own docstring).')
    print()
    print('scripts/measure_post_classical_repeated.py:116: "compression_ratio": compression_ratio(ciphertext_body)')
    print('  where ciphertext_body = stages["post_classical"]["ciphertext"] -- again the body alone.')
    print()
    print('scripts/measure_repeated_sample_stats.py: does not call compression_ratio() at all')
    print('  (it only measures entropy, chi_square, correlation -- no compression ratio column).')
    print()
    print('No script anywhere concatenates nonce+ciphertext+tag (full_aead_bytes) before calling')
    print('compression_ratio(). full_aead_bytes is used ONLY for size_overhead_full_aead_pct,')
    print('a separate metric, never for compression_ratio/entropy/chi_square/correlation.')

    print("\n=== Live check: text_small.txt, all three stages ===")
    key = _load_key()
    reference_sequence = _load_reference_sequence()
    with open(os.path.join(CORPUS_DIR, "text_small.txt"), "rb") as f:
        data = f.read()

    stages = pipeline_a_dna_plus_classical(data, key, reference_sequence)
    nonce = stages["post_classical"]["nonce"]
    ciphertext = stages["post_classical"]["ciphertext"]
    tag = stages["post_classical"]["tag"]
    full_aead_bytes = nonce + ciphertext + tag

    for label, stage_bytes in [
        ("input", stages["input"]),
        ("post_dna", stages["post_dna"]),
        ("post_classical (ciphertext body alone)", ciphertext),
        ("post_classical (full_aead_bytes, nonce+ciphertext+tag, for comparison only)", full_aead_bytes),
    ]:
        gz_input_len = len(stage_bytes)
        gz_output_len = len(gzip.compress(stage_bytes))
        ratio = compression_ratio(stage_bytes)
        print(f"  {label}:")
        print(f"    gzip input length:  {gz_input_len}")
        print(f"    gzip output length: {gz_output_len}")
        print(f"    compression_ratio(): {ratio!r}")


if __name__ == "__main__":
    run()
