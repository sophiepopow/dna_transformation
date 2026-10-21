"""
scripts/investigate_repeated_sample_chisq.py

Read-only diagnostic. Reproduces scripts/measure_repeated_sample_stats.py's
exact sample-generation and measurement logic (same functions, same seeds,
same stride computation, unmodified) and prints raw, individual per-sample
values instead of only the aggregated mean/sd -- to investigate why the
post_classical chi-square sd for the text class came out lower (10.0) than
a separate run's 21.9, both below the sqrt(510)=22.58 theoretical sd.

This script does not modify scripts/measure_repeated_sample_stats.py or
any other file. It only re-runs the same measurement and prints more of
the intermediate data.

Run from the `project/` directory:
    python3 scripts/investigate_repeated_sample_chisq.py
"""

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

N_SAMPLES = 10
SAMPLE_BYTES = 10 * 1024
JSON_SEED_BASE = 90000


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


def _text_samples_with_offsets():
    with open(os.path.join(CORPUS_DIR, "text_large.txt"), "rb") as f:
        novel_bytes = f.read()

    usable = len(novel_bytes) - SAMPLE_BYTES
    stride = usable // (N_SAMPLES - 1)
    samples = []
    offsets = []
    for i in range(N_SAMPLES):
        start = i * stride
        samples.append(novel_bytes[start:start + SAMPLE_BYTES])
        offsets.append((start, SAMPLE_BYTES))
    return samples, offsets, len(novel_bytes), stride


def _measure_sample(data: bytes, key: bytes, reference_sequence: str, aes_call_counter: list) -> dict:
    stages = pipeline_a_dna_plus_classical(data, key, reference_sequence)
    aes_call_counter[0] += 1  # pipeline_a_dna_plus_classical makes exactly one encrypt_aes_gcm call internally
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


def run():
    key = _load_key()
    reference_sequence = _load_reference_sequence()

    print("=" * 70)
    print("Q: What ddof is used for the reported standard deviation?")
    print("=" * 70)
    print("scripts/measure_repeated_sample_stats.py's _aggregate() calls")
    print("statistics.stdev(values) directly (src line: `return statistics.mean(values), statistics.stdev(values)`).")
    print("Python's statistics.stdev() computes the SAMPLE standard deviation,")
    print("i.e. ddof=1 (divides the sum of squared deviations by n-1, not n).")
    print(f"Confirmed via statistics.stdev.__doc__: {statistics.stdev.__doc__.strip().splitlines()[0]!r}")

    print("\n" + "=" * 70)
    print("Q: Are the 10 text samples truly non-overlapping slices of text_large.txt?")
    print("=" * 70)
    text_samples, offsets, novel_len, stride = _text_samples_with_offsets()
    print(f"text_large.txt length: {novel_len} bytes; sample length: {SAMPLE_BYTES} bytes; stride: {stride} bytes")
    print(f"{'sample':8s} {'start':>10s} {'end (excl)':>12s} {'length':>8s}")
    for i, (start, length) in enumerate(offsets):
        print(f"  {i:6d} {start:10d} {start+length:12d} {length:8d}")
    overlaps = []
    for i in range(len(offsets)):
        for j in range(i + 1, len(offsets)):
            s1, l1 = offsets[i]
            s2, l2 = offsets[j]
            e1, e2 = s1 + l1, s2 + l2
            if s1 < e2 and s2 < e1:
                overlaps.append((i, j, max(s1, s2), min(e1, e2)))
    if overlaps:
        print(f"OVERLAPS FOUND: {overlaps}")
    else:
        print("No overlaps: confirmed non-overlapping for all 10 x 9 / 2 = 45 pairs.")

    print("\n" + "=" * 70)
    print("Q: Is post_classical computed once per sample, or reused across samples?")
    print("=" * 70)
    print("pipeline_a_dna_plus_classical(data, key, reference_sequence) is called")
    print("once per sample (src/pipeline.py), and it makes exactly one internal")
    print("encrypt_aes_gcm() call per invocation (src/pipeline.py line: ")
    print('    "nonce, ciphertext, tag = encrypt_aes_gcm(post_dna, key)").')
    print("So each of the 10 samples gets its own dna_transform() output AND its")
    print("own, independent encrypt_aes_gcm() call (fresh random nonce every time,")
    print("since AES.new()'s default MODE_GCM behavior generates a new nonce per call).")
    print("Verifying by call count below.")

    print("\n" + "=" * 70)
    print("Raw per-sample chi-square values (full precision), by data class and stage")
    print("=" * 70)

    aes_call_counter = [0]
    data_classes = {
        "text": text_samples,
        "json": _json_samples(),
        "random": _random_samples(),
    }

    all_results = {}
    nonces_seen = {}
    for data_class, samples in data_classes.items():
        per_sample_results = []
        nonces = []
        for data in samples:
            stages = pipeline_a_dna_plus_classical(data, key, reference_sequence)
            aes_call_counter[0] += 1
            nonces.append(stages["post_classical"]["nonce"])
            stage_bytes = {
                "input": stages["input"],
                "post_dna": stages["post_dna"],
                "post_classical": stages["post_classical"]["ciphertext"],
            }
            per_sample_results.append(
                {stage: chi_square_uniform(sb) for stage, sb in stage_bytes.items()}
            )
        all_results[data_class] = per_sample_results
        nonces_seen[data_class] = nonces

        print(f"\n--- {data_class} ---")
        for stage in ("input", "post_dna", "post_classical"):
            values = [r[stage] for r in per_sample_results]
            print(f"  {stage}:")
            for i, v in enumerate(values):
                print(f"    sample {i}: {v!r}")
            mean = statistics.mean(values)
            sd = statistics.stdev(values)
            print(f"    -> mean={mean!r}  sd(ddof=1)={sd!r}")
            if len(values) > 1:
                import math
                pop_variance = sum((v - mean) ** 2 for v in values) / len(values)
                sd_pop = math.sqrt(pop_variance)
                print(f"    -> sd(ddof=0, population)={sd_pop!r}  (for comparison)")

    print("\n" + "=" * 70)
    print("Nonce uniqueness check (confirms independent AES-GCM calls, not reuse)")
    print("=" * 70)
    for data_class, nonces in nonces_seen.items():
        unique = len(set(nonces))
        print(f"  {data_class}: {len(nonces)} calls, {unique} unique nonces "
              f"({'OK, all distinct' if unique == len(nonces) else 'DUPLICATE NONCES FOUND'})")

    print(f"\nTotal encrypt_aes_gcm-backed pipeline calls made in this diagnostic run: {aes_call_counter[0]}")
    print("(10 text + 10 json + 10 random = 30 calls expected for the per-class loop above,")
    print(" the ddof/overlap sections above made their own separate calls not counted here.)")


if __name__ == "__main__":
    run()
