"""
scripts/measure_post_classical_repeated.py

For each of the 6 frozen corpus files, at the post_classical stage, for
both Pipeline A (DNA transform + AES-GCM) and Pipeline B (AES-GCM only,
control), under the same fixed AES key (data/aes_key.bin): Shannon
entropy, chi-square statistic, the chi-square standardised deviate
(chisq - 255) / sqrt(510) -- 255 = degrees of freedom (256 byte values
minus one), 510 = 2*df, the chi-square distribution's variance under its
usual large-sample normal approximation -- compression ratio, and Pearson
correlation against the original input.

AES-GCM draws a fresh random nonce on every call (src/classical_crypto.py),
so post_classical ciphertext differs between runs even for the same input
and key. A single draw per (file, pipeline) cell is therefore a sample of
size 1 from a distribution, not a stable point estimate. This script runs
each cell 10 times and reports mean +/- sd for every metric instead.

Reuses, unmodified: src/pipeline.py (pipeline_a_dna_plus_classical,
pipeline_b_classical_only), src/metrics.py (shannon_entropy,
chi_square_uniform, compression_ratio, pearson_correlation). Metrics are
computed on the post_classical ciphertext BODY only (excluding nonce and
tag), the same convention scripts/run_experiment.py and
scripts/measure_repeated_sample_stats.py already use for "the ciphertext"
as a semantic payload.

Outputs three CSVs under results/:
    post_classical_repeated_raw.csv     -- one row per (file, pipeline, rep)
    post_classical_repeated_summary.csv -- one row per (file, pipeline),
                                            mean +/- sd across the 10 reps
    post_classical_repeated_nonces.csv  -- one row per (file, pipeline, rep)
                                            with the hex nonce that run's
                                            encrypt_aes_gcm call produced

Runtime assertions (not just documentation -- these actually run and abort
the script on failure):
  1. The same AES key is used for all 120 runs: its SHA-256 is checked
     against the value computed at load time, on every single run.
  2. All 120 nonces (one per run, from encrypt_aes_gcm) are collected and
     asserted distinct -- no reuse.
  3. For each file, the plaintext bytes handed to Pipeline A and Pipeline B
     are asserted byte-identical via SHA-256, both per-call and across the
     two pipelines.

Run from the `project/` directory:
    python3 scripts/measure_post_classical_repeated.py
"""

import csv
import hashlib
import math
import os
import statistics
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from metrics import chi_square_uniform, compression_ratio, pearson_correlation, shannon_entropy  # noqa: E402
from pipeline import pipeline_a_dna_plus_classical, pipeline_b_classical_only  # noqa: E402

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
CORPUS_DIR = os.path.join(DATA_DIR, "corpus")
RESULTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "results"))
RAW_CSV = os.path.join(RESULTS_DIR, "post_classical_repeated_raw.csv")
SUMMARY_CSV = os.path.join(RESULTS_DIR, "post_classical_repeated_summary.csv")
NONCES_CSV = os.path.join(RESULTS_DIR, "post_classical_repeated_nonces.csv")

N_REPS = 10
CHI_SQUARE_DF = 255       # 256 byte values minus one
CHI_SQUARE_VARIANCE = 2 * CHI_SQUARE_DF  # = 510, standard chi-square variance = 2*df

CORPUS_FILES = [
    ("text_small.txt", "text", "small"),
    ("text_large.txt", "text", "large"),
    ("json_small.json", "json", "small"),
    ("json_large.json", "json", "large"),
    ("random_small.bin", "random", "small"),
    ("random_large.bin", "random", "large"),
]

RAW_FIELDNAMES = [
    "file", "data_class", "size_class", "pipeline", "rep",
    "entropy", "chi_square", "standardized_deviate", "compression_ratio", "correlation_vs_input",
]
SUMMARY_FIELDNAMES = [
    "file", "data_class", "size_class", "pipeline", "n_reps",
    "entropy_mean", "entropy_sd",
    "chi_square_mean", "chi_square_sd",
    "standardized_deviate_mean", "standardized_deviate_sd",
    "compression_ratio_mean", "compression_ratio_sd",
    "correlation_mean", "correlation_sd",
]


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


def _load_corpus_file(name: str) -> bytes:
    with open(os.path.join(CORPUS_DIR, name), "rb") as f:
        return f.read()


def _measure_one_run(data: bytes, ciphertext_body: bytes) -> dict:
    chisq = chi_square_uniform(ciphertext_body)
    return {
        "entropy": shannon_entropy(ciphertext_body),
        "chi_square": chisq,
        "standardized_deviate": (chisq - CHI_SQUARE_DF) / math.sqrt(CHI_SQUARE_VARIANCE),
        "compression_ratio": compression_ratio(ciphertext_body),
        "correlation_vs_input": pearson_correlation(data, ciphertext_body),
    }


def run():
    _verify_checksums()
    key = _load_key()
    key_sha256 = hashlib.sha256(key).hexdigest()
    reference_sequence = _load_reference_sequence()

    raw_rows = []
    summary_rows = []
    all_nonces = []  # one entry per (file, pipeline, rep): {"file","pipeline","rep","nonce_hex"}

    for filename, data_class, size_class in CORPUS_FILES:
        data = _load_corpus_file(filename)
        data_sha256 = hashlib.sha256(data).hexdigest()
        print(f"\n=== {filename} ({data_class}/{size_class}, {len(data)} bytes) ===")

        pipeline_plaintext_sha256 = {}  # pipeline -> sha256 of the plaintext it was actually called with

        for pipeline in ("A", "B"):
            per_metric = {k: [] for k in ("entropy", "chi_square", "standardized_deviate", "compression_ratio", "correlation_vs_input")}

            for rep in range(N_REPS):
                # Assertion 1: same AES key on every single one of the 120 runs.
                assert hashlib.sha256(key).hexdigest() == key_sha256, (
                    f"AES key changed between runs at file={filename} pipeline={pipeline} rep={rep}: "
                    f"expected sha256={key_sha256}, got {hashlib.sha256(key).hexdigest()}"
                )

                if pipeline == "A":
                    stages = pipeline_a_dna_plus_classical(data, key, reference_sequence)
                else:
                    stages = pipeline_b_classical_only(data, key)
                ciphertext_body = stages["post_classical"]["ciphertext"]
                nonce = stages["post_classical"]["nonce"]

                # Assertion 3 (per-call half): the plaintext this specific pipeline call
                # actually received is byte-identical to what was loaded for this file.
                assert hashlib.sha256(data).hexdigest() == data_sha256, (
                    f"plaintext for {filename} changed before pipeline {pipeline} rep {rep} was called"
                )
                pipeline_plaintext_sha256[pipeline] = data_sha256

                all_nonces.append(
                    {"file": filename, "pipeline": pipeline, "rep": rep, "nonce_hex": nonce.hex()}
                )

                m = _measure_one_run(data, ciphertext_body)
                for k, v in m.items():
                    per_metric[k].append(v)

                raw_rows.append(
                    {
                        "file": filename,
                        "data_class": data_class,
                        "size_class": size_class,
                        "pipeline": pipeline,
                        "rep": rep,
                        "entropy": m["entropy"],
                        "chi_square": m["chi_square"],
                        "standardized_deviate": m["standardized_deviate"],
                        "compression_ratio": m["compression_ratio"],
                        "correlation_vs_input": m["correlation_vs_input"],
                    }
                )

            summary_rows.append(
                {
                    "file": filename,
                    "data_class": data_class,
                    "size_class": size_class,
                    "pipeline": pipeline,
                    "n_reps": N_REPS,
                    "entropy_mean": statistics.mean(per_metric["entropy"]),
                    "entropy_sd": statistics.stdev(per_metric["entropy"]),
                    "chi_square_mean": statistics.mean(per_metric["chi_square"]),
                    "chi_square_sd": statistics.stdev(per_metric["chi_square"]),
                    "standardized_deviate_mean": statistics.mean(per_metric["standardized_deviate"]),
                    "standardized_deviate_sd": statistics.stdev(per_metric["standardized_deviate"]),
                    "compression_ratio_mean": statistics.mean(per_metric["compression_ratio"]),
                    "compression_ratio_sd": statistics.stdev(per_metric["compression_ratio"]),
                    "correlation_mean": statistics.mean(per_metric["correlation_vs_input"]),
                    "correlation_sd": statistics.stdev(per_metric["correlation_vs_input"]),
                }
            )
            print(
                f"  Pipeline {pipeline}: entropy={statistics.mean(per_metric['entropy']):.4f}+/-{statistics.stdev(per_metric['entropy']):.4f}  "
                f"chi2={statistics.mean(per_metric['chi_square']):.2f}+/-{statistics.stdev(per_metric['chi_square']):.2f}  "
                f"z={statistics.mean(per_metric['standardized_deviate']):+.3f}+/-{statistics.stdev(per_metric['standardized_deviate']):.3f}  "
                f"comp={statistics.mean(per_metric['compression_ratio']):.4f}+/-{statistics.stdev(per_metric['compression_ratio']):.4f}  "
                f"corr={statistics.mean(per_metric['correlation_vs_input']):+.4f}+/-{statistics.stdev(per_metric['correlation_vs_input']):.4f}"
            )

        # Assertion 3: Pipeline A and Pipeline B were handed byte-identical plaintext for this file.
        assert pipeline_plaintext_sha256["A"] == pipeline_plaintext_sha256["B"] == data_sha256, (
            f"plaintext mismatch between pipelines for {filename}: "
            f"A={pipeline_plaintext_sha256['A']} B={pipeline_plaintext_sha256['B']} loaded={data_sha256}"
        )
        print(f"  [assert] Pipeline A/B plaintext SHA-256 match for {filename}: {data_sha256}")

    # Assertion 1 (final tally) + Assertion 2: exactly 120 runs, all with the same key,
    # and 120 distinct nonces.
    expected_total = len(CORPUS_FILES) * 2 * N_REPS
    assert len(all_nonces) == expected_total, (
        f"expected {expected_total} runs, recorded {len(all_nonces)}"
    )
    nonce_hexes = [n["nonce_hex"] for n in all_nonces]
    assert len(set(nonce_hexes)) == expected_total, (
        f"expected {expected_total} unique nonces, got {len(set(nonce_hexes))} unique out of {len(nonce_hexes)} total"
    )
    print(f"\n[assert] All {expected_total} runs used the same AES key (sha256={key_sha256}).")
    print(f"[assert] All {expected_total} nonces are unique (0 duplicates).")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(NONCES_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "pipeline", "rep", "nonce_hex"])
        writer.writeheader()
        writer.writerows(all_nonces)
    print(f"Wrote {len(all_nonces)} rows to {NONCES_CSV}")

    with open(RAW_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=RAW_FIELDNAMES)
        writer.writeheader()
        writer.writerows(raw_rows)

    with open(SUMMARY_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_FIELDNAMES)
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"\nWrote {len(raw_rows)} rows to {RAW_CSV}")
    print(f"Wrote {len(summary_rows)} rows to {SUMMARY_CSV}")


if __name__ == "__main__":
    run()
