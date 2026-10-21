"""
scripts/measure_repeated_sample_post_classical_n50_independent_text.py

Task 2 follow-up: re-runs the n=50 text measurement using 50 genuinely
non-overlapping 10240-byte slices, now that scripts/build_text_pool.py
has extended the text pool beyond text_large.txt's 19-slice limit with
two more public-domain Project Gutenberg texts
(data/corpus/text_pool_alice.txt, data/corpus/text_pool_mobydick.txt).

Slice allocation (sequential, non-overlapping, no cycling): text_large.txt
contributes its full 19 available slices, text_pool_alice.txt contributes
its full 15, and text_pool_mobydick.txt contributes 16 more (out of the
122 it has available) to reach 50 total. This uses genuinely distinct
plaintext content for every one of the 50 samples -- no repeats.

Does not touch JSON or random sampling (unchanged from
measure_repeated_sample_post_classical_n50.py; not re-run here since
this script only concerns the text class), and does not change any
metric definition (same src/metrics.py functions, same post_classical-only
scope, same Pipeline A, same fixed AES key).

Outputs:
    results/repeated_sample_post_classical_n50_text_independent_raw.csv
    -- one row per sample (50 rows): source_file, byte_offset,
       entropy_post_classical, chisq_post_classical, correlation_post_classical

Run from the `project/` directory:
    python3 scripts/measure_repeated_sample_post_classical_n50_independent_text.py
"""

import csv
import hashlib
import os
import statistics
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from metrics import chi_square_uniform, pearson_correlation, shannon_entropy  # noqa: E402
from pipeline import pipeline_a_dna_plus_classical  # noqa: E402

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
CORPUS_DIR = os.path.join(DATA_DIR, "corpus")
RESULTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "results"))
RAW_CSV = os.path.join(RESULTS_DIR, "repeated_sample_post_classical_n50_text_independent_raw.csv")
SUMMARY_CSV = os.path.join(RESULTS_DIR, "repeated_sample_post_classical_n50_text_independent_summary.csv")

N_SAMPLES = 50
SAMPLE_BYTES = 10 * 1024

SOURCE_FILES = ["text_large.txt", "text_pool_alice.txt", "text_pool_mobydick.txt"]


def _verify_checksums():
    manifest_path = os.path.join(CORPUS_DIR, "CHECKSUMS.sha256")
    with open(manifest_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            expected_hash, filename = line.split(maxsplit=1)
            path = os.path.join(CORPUS_DIR, filename.strip())
            with open(path, "rb") as fh:
                actual_hash = hashlib.sha256(fh.read()).hexdigest()
            assert actual_hash == expected_hash, f"checksum mismatch for {filename}"


def _load_key() -> bytes:
    with open(os.path.join(DATA_DIR, "aes_key.bin"), "rb") as f:
        return f.read()


def _load_reference_sequence() -> str:
    with open(os.path.join(DATA_DIR, "reference_sequence.txt")) as f:
        return f.read().strip()


def _build_50_nonoverlapping_slices():
    slices = []  # list of (source_file, byte_offset, data)
    for filename in SOURCE_FILES:
        if len(slices) >= N_SAMPLES:
            break
        path = os.path.join(CORPUS_DIR, filename)
        with open(path, "rb") as f:
            content = f.read()
        max_slices_here = len(content) // SAMPLE_BYTES
        needed = N_SAMPLES - len(slices)
        take = min(max_slices_here, needed)
        for i in range(take):
            offset = i * SAMPLE_BYTES
            slices.append((filename, offset, content[offset:offset + SAMPLE_BYTES]))
        print(f"  {filename}: {len(content)} bytes, {max_slices_here} slices available, took {take}")
    assert len(slices) == N_SAMPLES, f"only assembled {len(slices)} non-overlapping slices, needed {N_SAMPLES}"

    # Confirm no overlap within each source file (different files can't overlap by definition).
    by_file = {}
    for filename, offset, _ in slices:
        by_file.setdefault(filename, []).append(offset)
    for filename, offsets in by_file.items():
        offsets_sorted = sorted(offsets)
        for a, b in zip(offsets_sorted, offsets_sorted[1:]):
            assert b >= a + SAMPLE_BYTES, f"overlap detected in {filename}: offsets {a} and {b}"

    return slices


def _measure_post_classical(data: bytes, key: bytes, reference_sequence: str) -> dict:
    stages = pipeline_a_dna_plus_classical(data, key, reference_sequence)
    ciphertext_body = stages["post_classical"]["ciphertext"]
    return {
        "entropy": shannon_entropy(ciphertext_body),
        "chi_square": chi_square_uniform(ciphertext_body),
        "correlation": pearson_correlation(data, ciphertext_body),
    }


def run():
    _verify_checksums()
    key = _load_key()
    reference_sequence = _load_reference_sequence()

    print("Assembling 50 non-overlapping 10240-byte text slices across the pool:")
    slices = _build_50_nonoverlapping_slices()
    print(f"Assembled {len(slices)} slices, all confirmed non-overlapping within each source file.\n")

    raw_rows = []
    per_metric = {"entropy": [], "chi_square": [], "correlation": []}

    for i, (source_file, offset, data) in enumerate(slices):
        m = _measure_post_classical(data, key, reference_sequence)
        for k, v in m.items():
            per_metric[k].append(v)
        raw_rows.append(
            {
                "sample_index": i,
                "source_file": source_file,
                "byte_offset": offset,
                "entropy_post_classical": m["entropy"],
                "chisq_post_classical": m["chi_square"],
                "correlation_post_classical": m["correlation"],
            }
        )

    entropy_mean, entropy_sd = statistics.mean(per_metric["entropy"]), statistics.stdev(per_metric["entropy"])
    chisq_mean, chisq_sd = statistics.mean(per_metric["chi_square"]), statistics.stdev(per_metric["chi_square"])
    corr_mean, corr_sd = statistics.mean(per_metric["correlation"]), statistics.stdev(per_metric["correlation"])

    print(f"entropy: mean={entropy_mean:.6f} sd={entropy_sd:.6f}")
    print(f"chi_square: mean={chisq_mean:.4f} sd={chisq_sd:.4f}  (theoretical sd=sqrt(510)={510**0.5:.4f})")
    print(f"correlation: mean={corr_mean:+.6f} sd={corr_sd:.6f}")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(RAW_CSV, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["sample_index", "source_file", "byte_offset",
                        "entropy_post_classical", "chisq_post_classical", "correlation_post_classical"],
        )
        writer.writeheader()
        writer.writerows(raw_rows)

    with open(SUMMARY_CSV, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["n_samples", "entropy_mean", "entropy_sd", "chi_square_mean", "chi_square_sd",
                        "correlation_mean", "correlation_sd"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "n_samples": N_SAMPLES,
                "entropy_mean": entropy_mean,
                "entropy_sd": entropy_sd,
                "chi_square_mean": chisq_mean,
                "chi_square_sd": chisq_sd,
                "correlation_mean": corr_mean,
                "correlation_sd": corr_sd,
            }
        )

    print(f"\nWrote {len(raw_rows)} rows to {RAW_CSV}")
    print(f"Wrote summary to {SUMMARY_CSV}")


if __name__ == "__main__":
    run()
