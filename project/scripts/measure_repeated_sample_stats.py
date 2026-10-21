"""
scripts/measure_repeated_sample_stats.py

Follow-up strengthening measurement, requested directly during thesis
review: entropy, chi-square, and Pearson correlation (results
Section 7.1 / 7.2) were each computed from a single sample per data
class -- one run of text_small.txt, one of json_small.json, one of
random_small.bin. Avalanche was already re-measured over 2,000 trials
with a reported mean and stdev (scripts/measure_dna_transform_avalanche.py);
these three metrics had no equivalent.

This script closes that gap. For each data class, it draws 10
independent ~10 KB samples:

  - random: 10 fresh os.urandom(10240) draws.
  - json:   10 freshly generated JSON logs, each with its own seed
            (scripts/build_corpus.py's build_json_corpus, reused
            unmodified, seeds distinct from the frozen corpus's seed
            so these are genuinely new draws, not the frozen file).
  - text:   10 non-overlapping ~10 KB slices of the frozen
            text_large.txt (itself a slice of the same public-domain
            novel used to build the frozen corpus, see
            data/corpus/SOURCES.md), spaced evenly across its ~200 KB
            so no two slices share content.

Each sample is run through Pipeline A's stages (input -> post_dna ->
post_classical ciphertext body), and entropy / chi-square / correlation
are computed at each stage for each sample. The script reports mean and
stdev across the 10 samples per (data class, stage), the same
statistical treatment already used for avalanche.

None of these samples touch or modify the frozen corpus
(data/corpus/*, git tag corpus-v1-frozen) -- they are generated fresh at
run time, not written to disk, used only to compute the statistics this
script prints and to write results/repeated_sample_stats.csv.

Reuses, unmodified: src/metrics.py (shannon_entropy, chi_square_uniform,
pearson_correlation), src/pipeline.py (pipeline_a_dna_plus_classical),
scripts/build_corpus.py (build_json_corpus).

Run from the `project/` directory:
    python3 scripts/measure_repeated_sample_stats.py
"""

import csv
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
OUTPUT_CSV = os.path.join(RESULTS_DIR, "repeated_sample_stats.csv")

N_SAMPLES = 10
SAMPLE_BYTES = 10 * 1024
JSON_SEED_BASE = 90000  # distinct from build_corpus.py's JSON_SEED (20260816/...)


def _load_key() -> bytes:
    with open(os.path.join(DATA_DIR, "aes_key.bin"), "rb") as f:
        return f.read()


def _load_reference_sequence() -> str:
    with open(os.path.join(DATA_DIR, "reference_sequence.txt")) as f:
        return f.read().strip()


def _random_samples() -> list:
    return [os.urandom(SAMPLE_BYTES) for _ in range(N_SAMPLES)]


def _json_samples() -> list:
    samples = []
    for i in range(N_SAMPLES):
        serialized = build_json_corpus(SAMPLE_BYTES, seed=JSON_SEED_BASE + i)
        samples.append(serialized.encode("utf-8"))
    return samples


def _text_samples() -> list:
    with open(os.path.join(CORPUS_DIR, "text_large.txt"), "rb") as f:
        novel_bytes = f.read()

    usable = len(novel_bytes) - SAMPLE_BYTES
    stride = usable // (N_SAMPLES - 1)
    samples = []
    for i in range(N_SAMPLES):
        start = i * stride
        samples.append(novel_bytes[start:start + SAMPLE_BYTES])
    return samples


def _measure_sample(data: bytes, key: bytes, reference_sequence: str) -> dict:
    stages = pipeline_a_dna_plus_classical(data, key, reference_sequence)
    stage_bytes = {
        "input": stages["input"],
        "post_dna": stages["post_dna"],
        "post_classical": stages["post_classical"]["ciphertext"],
    }
    result = {}
    for stage, sb in stage_bytes.items():
        result[stage] = {
            "entropy": shannon_entropy(sb),
            "chi_square": chi_square_uniform(sb),
            "correlation": pearson_correlation(data, sb),
        }
    return result


def _aggregate(per_sample: list, stage: str, metric: str) -> tuple:
    values = [s[stage][metric] for s in per_sample]
    return statistics.mean(values), statistics.stdev(values)


def run():
    key = _load_key()
    reference_sequence = _load_reference_sequence()

    data_classes = {
        "text": _text_samples(),
        "json": _json_samples(),
        "random": _random_samples(),
    }

    rows = []
    for data_class, samples in data_classes.items():
        print(f"\n=== {data_class} ({N_SAMPLES} samples, {SAMPLE_BYTES} bytes each) ===")
        per_sample = [_measure_sample(s, key, reference_sequence) for s in samples]

        for stage in ("input", "post_dna", "post_classical"):
            entropy_mean, entropy_stdev = _aggregate(per_sample, stage, "entropy")
            chi2_mean, chi2_stdev = _aggregate(per_sample, stage, "chi_square")
            corr_mean, corr_stdev = _aggregate(per_sample, stage, "correlation")

            print(
                f"  {stage:16s} entropy={entropy_mean:.4f}+/-{entropy_stdev:.4f}  "
                f"chi2={chi2_mean:.3f}+/-{chi2_stdev:.3f}  "
                f"corr={corr_mean:+.4f}+/-{corr_stdev:.4f}"
            )

            rows.append(
                {
                    "data_class": data_class,
                    "stage": stage,
                    "n_samples": N_SAMPLES,
                    "entropy_mean": entropy_mean,
                    "entropy_stdev": entropy_stdev,
                    "chi_square_mean": chi2_mean,
                    "chi_square_stdev": chi2_stdev,
                    "correlation_mean": corr_mean,
                    "correlation_stdev": corr_stdev,
                }
            )

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "data_class",
                "stage",
                "n_samples",
                "entropy_mean",
                "entropy_stdev",
                "chi_square_mean",
                "chi_square_stdev",
                "correlation_mean",
                "correlation_stdev",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"\nWrote {len(rows)} rows to {OUTPUT_CSV}")


if __name__ == "__main__":
    run()
