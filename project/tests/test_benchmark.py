"""
tests/test_benchmark.py

Unit tests for src/benchmark.py: time_stage, benchmark_pipeline,
throughput, size_overhead. Runs the harness on both experimental pipelines
(src/pipeline.py) using data/corpus/text_small.txt, the fixed experiment
AES key (data/aes_key.bin), and the fixed reference DNA sequence
(data/reference_sequence.txt) -- loaded the same way tests/test_pipeline.py
does.

See src/benchmark.py's module docstring ("Design point") for why
benchmark_pipeline takes an optional reference_sequence kwarg beyond the
milestone spec's literal 4-argument signature, and why Pipeline B's
dna_transform_ms is 0.0 rather than a positive float: that asymmetry is
intentional (Pipeline B has no DNA stage), so this suite checks
"positive" only where a stage genuinely runs, not uniformly across every
value in every returned dict.
"""

import math
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from benchmark import time_stage, benchmark_pipeline, throughput, size_overhead
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


class TestTimeStage:
    def test_returns_expected_keys_and_sample_count(self):
        n_reps = 10
        result = time_stage(time.sleep, 0.001, n_reps=n_reps)
        assert set(result.keys()) == {"median_ms", "iqr_ms", "all_samples"}
        assert len(result["all_samples"]) == n_reps

    def test_values_are_positive_floats(self):
        result = time_stage(time.sleep, 0.001, n_reps=10)
        assert isinstance(result["median_ms"], float)
        assert result["median_ms"] > 0
        assert isinstance(result["iqr_ms"], float)
        assert result["iqr_ms"] >= 0
        assert all(isinstance(s, float) and s > 0 for s in result["all_samples"])

    def test_default_n_reps_is_20_samples(self):
        result = time_stage(lambda: None)
        assert len(result["all_samples"]) == 20


class TestBenchmarkPipelineA:
    def test_stage_timings_positive_floats(self):
        result = benchmark_pipeline(
            pipeline_a_dna_plus_classical,
            TEXT_SMALL,
            KEY,
            n_reps=5,
            reference_sequence=REFERENCE_SEQUENCE,
        )
        for k in ("dna_transform_ms", "classical_encrypt_ms", "total_ms"):
            assert isinstance(result[k], float)
            assert result[k] > 0, f"{k} expected positive, got {result[k]}"
        assert result["dna_transform_stats"] is not None

    def test_finite(self):
        result = benchmark_pipeline(
            pipeline_a_dna_plus_classical,
            TEXT_SMALL,
            KEY,
            n_reps=5,
            reference_sequence=REFERENCE_SEQUENCE,
        )
        for k in ("dna_transform_ms", "classical_encrypt_ms", "total_ms"):
            assert math.isfinite(result[k])


class TestBenchmarkPipelineB:
    def test_stage_timings(self):
        result = benchmark_pipeline(
            pipeline_b_classical_only, TEXT_SMALL, KEY, n_reps=5
        )
        # Pipeline B has no DNA stage: dna_transform_ms is defined as 0.0
        # (see src/benchmark.py's design-point docstring), not a positive
        # float -- this is intentional, not a bug.
        assert result["dna_transform_ms"] == 0.0
        assert result["dna_transform_stats"] is None
        for k in ("classical_encrypt_ms", "total_ms"):
            assert isinstance(result[k], float)
            assert result[k] > 0, f"{k} expected positive, got {result[k]}"

    def test_finite(self):
        result = benchmark_pipeline(
            pipeline_b_classical_only, TEXT_SMALL, KEY, n_reps=5
        )
        for k in ("dna_transform_ms", "classical_encrypt_ms", "total_ms"):
            assert math.isfinite(result[k])


class TestThroughput:
    def test_positive_and_finite(self):
        value = throughput(len(TEXT_SMALL), total_ms=10.0)
        assert isinstance(value, float)
        assert value > 0
        assert math.isfinite(value)

    def test_known_value(self):
        # 1000 bytes in 1000 ms == 1000 bytes/sec.
        assert throughput(1000, 1000.0) == 1000.0

    def test_zero_size_returns_zero(self):
        assert throughput(0, 10.0) == 0.0


class TestSizeOverhead:
    def test_larger_ciphertext_is_positive_overhead(self):
        plaintext = b"a" * 100
        ciphertext = b"a" * 116  # AES-GCM tag adds 16 bytes, e.g.
        value = size_overhead(plaintext, ciphertext)
        assert isinstance(value, float)
        assert value == 16.0

    def test_equal_size_is_zero_overhead(self):
        assert size_overhead(b"abc", b"xyz") == 0.0

    def test_empty_plaintext_returns_zero(self):
        assert size_overhead(b"", b"abc") == 0.0

    def test_real_pipeline_ciphertext_overhead_is_finite(self):
        stages_b = pipeline_b_classical_only(TEXT_SMALL, KEY)
        ciphertext = stages_b["post_classical"]["ciphertext"]
        value = size_overhead(TEXT_SMALL, ciphertext)
        assert math.isfinite(value)
