"""
scripts/measure_repeated_sample_post_classical_n50.py

Re-run of scripts/measure_repeated_sample_stats.py's post_classical
measurement at n=50 instead of n=10, restricted to post_classical only.
post_dna is deterministic given its input (Section 7.2/7.3 already
report it exactly at n=10); this script does not recompute it. input-stage
values are likewise not recomputed/reported here.

Sample generation, extended from n=10 to n=50:

- text: text_large.txt (204799 bytes) does NOT allow 50 non-overlapping
  10240-byte slices -- that would need 512000 bytes, about 2.5x the file's
  actual size (max possible non-overlapping back-to-back slices: 19).
  So the same 10 original non-overlapping offsets from
  measure_repeated_sample_stats.py are reused, CYCLED: sample i uses
  offset original_offsets[i % 10]. This gives 5 independent post_classical
  draws (fresh AES-GCM nonce each) per original text slice, not 50
  independent plaintexts. Reported explicitly per-sample so this is
  visible in the raw data, not hidden by an aggregate.

- json: the same generator (scripts/build_corpus.py's build_json_corpus,
  unmodified) with 50 distinct seeds, JSON_SEED_BASE + i for i in 0..49 --
  the first 10 (i=0..9) are identical to measure_repeated_sample_stats.py's
  original 10 seeds; i=10..49 are 40 new, previously-unused seeds.

- random: 50 fresh, independent os.urandom() draws (no seed, matching the
  original script's approach exactly, just 50 instead of 10).

Each of the 150 (3 classes x 50 samples) samples is run once through
Pipeline A (src/pipeline.py's pipeline_a_dna_plus_classical, unmodified),
and entropy / chi-square / Pearson correlation are computed on the
post_classical ciphertext body (excluding nonce/tag), reusing
src/metrics.py unmodified.

Outputs two CSVs under results/:
    repeated_sample_post_classical_n50_raw.csv     -- one row per sample (150 rows)
    repeated_sample_post_classical_n50_summary.csv -- one row per data class (3 rows),
                                                       mean +/- sd across the 50 samples

Run from the `project/` directory:
    python3 scripts/measure_repeated_sample_post_classical_n50.py
"""

import csv
import hashlib
import os
import statistics
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from metrics import chi_square_uniform, pearson_correlation, shannon_entropy  # noqa: E402
from pipeline import pipeline_a_dna_plus_classical  # noqa: E402
from build_corpus import build_json_corpus  # noqa: E402

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
CORPUS_DIR = os.path.join(DATA_DIR, "corpus")
RESULTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "results"))
RAW_CSV = os.path.join(RESULTS_DIR, "repeated_sample_post_classical_n50_raw.csv")
SUMMARY_CSV = os.path.join(RESULTS_DIR, "repeated_sample_post_classical_n50_summary.csv")

N_SAMPLES = 50
N_ORIGINAL_TEXT_OFFSETS = 10
SAMPLE_BYTES = 10 * 1024
JSON_SEED_BASE = 90000  # same base as measure_repeated_sample_stats.py


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


def _original_text_offsets(novel_bytes: bytes) -> list:
    """The exact same 10 offsets measure_repeated_sample_stats.py computes."""
    usable = len(novel_bytes) - SAMPLE_BYTES
    stride = usable // (N_ORIGINAL_TEXT_OFFSETS - 1)
    return [i * stride for i in range(N_ORIGINAL_TEXT_OFFSETS)]


def _text_samples_cycled():
    with open(os.path.join(CORPUS_DIR, "text_large.txt"), "rb") as f:
        novel_bytes = f.read()

    max_nonoverlapping = len(novel_bytes) // SAMPLE_BYTES
    print(f"text_large.txt is {len(novel_bytes)} bytes; 50 non-overlapping {SAMPLE_BYTES}-byte "
          f"slices would need {50 * SAMPLE_BYTES} bytes. Max possible non-overlapping slices: "
          f"{max_nonoverlapping}. NOT ENOUGH for 50 -> cycling the original {N_ORIGINAL_TEXT_OFFSETS} offsets.")

    offsets = _original_text_offsets(novel_bytes)
    samples = []
    used_offsets = []
    for i in range(N_SAMPLES):
        offset = offsets[i % N_ORIGINAL_TEXT_OFFSETS]
        samples.append(novel_bytes[offset:offset + SAMPLE_BYTES])
        used_offsets.append(offset)
    return samples, used_offsets


def _json_samples():
    samples = []
    seeds = []
    for i in range(N_SAMPLES):
        seed = JSON_SEED_BASE + i
        samples.append(build_json_corpus(SAMPLE_BYTES, seed=seed).encode("utf-8"))
        seeds.append(seed)
    return samples, seeds


def _random_samples():
    return [os.urandom(SAMPLE_BYTES) for _ in range(N_SAMPLES)], [None] * N_SAMPLES


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

    text_samples, text_offsets = _text_samples_cycled()
    json_samples, json_seeds = _json_samples()
    random_samples, random_placeholders = _random_samples()

    data_classes = {
        "text": (text_samples, text_offsets, "text_slice_offset"),
        "json": (json_samples, json_seeds, "json_seed"),
        "random": (random_samples, random_placeholders, "random_draw_index"),
    }

    raw_rows = []
    summary_rows = []

    for data_class, (samples, provenance, provenance_field) in data_classes.items():
        print(f"\n=== {data_class} (n={N_SAMPLES}) ===")
        per_metric = {"entropy": [], "chi_square": [], "correlation": []}

        for i, data in enumerate(samples):
            m = _measure_post_classical(data, key, reference_sequence)
            for k, v in m.items():
                per_metric[k].append(v)

            prov_value = provenance[i] if provenance[i] is not None else i
            raw_rows.append(
                {
                    "data_class": data_class,
                    "sample_index": i,
                    "provenance_field": provenance_field,
                    "provenance_value": prov_value,
                    "entropy_post_classical": m["entropy"],
                    "chisq_post_classical": m["chi_square"],
                    "correlation_post_classical": m["correlation"],
                }
            )

        entropy_mean, entropy_sd = statistics.mean(per_metric["entropy"]), statistics.stdev(per_metric["entropy"])
        chisq_mean, chisq_sd = statistics.mean(per_metric["chi_square"]), statistics.stdev(per_metric["chi_square"])
        corr_mean, corr_sd = statistics.mean(per_metric["correlation"]), statistics.stdev(per_metric["correlation"])

        print(f"  entropy: mean={entropy_mean:.6f} sd={entropy_sd:.6f}")
        print(f"  chi_square: mean={chisq_mean:.4f} sd={chisq_sd:.4f}  (theoretical sd=sqrt(510)={510**0.5:.4f})")
        print(f"  correlation: mean={corr_mean:+.6f} sd={corr_sd:.6f}")

        summary_rows.append(
            {
                "data_class": data_class,
                "n_samples": N_SAMPLES,
                "entropy_mean": entropy_mean,
                "entropy_sd": entropy_sd,
                "chi_square_mean": chisq_mean,
                "chi_square_sd": chisq_sd,
                "correlation_mean": corr_mean,
                "correlation_sd": corr_sd,
            }
        )

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(RAW_CSV, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "data_class", "sample_index", "provenance_field", "provenance_value",
                "entropy_post_classical", "chisq_post_classical", "correlation_post_classical",
            ],
        )
        writer.writeheader()
        writer.writerows(raw_rows)

    with open(SUMMARY_CSV, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "data_class", "n_samples", "entropy_mean", "entropy_sd",
                "chi_square_mean", "chi_square_sd", "correlation_mean", "correlation_sd",
            ],
        )
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"\nWrote {len(raw_rows)} rows to {RAW_CSV}")
    print(f"Wrote {len(summary_rows)} rows to {SUMMARY_CSV}")


if __name__ == "__main__":
    run()
