"""
scripts/measure_reference_sequence_factorial.py

Follow-up to Section 7.4 of the thesis, which found that the measured
entropy gap at the post_dna stage depends heavily on which reference
sequence is used, but only ever compared two sequences that differed on
two axes at once:

  - base balance (uniform A/T/C/G counts vs. skewed)
  - S mod 4, where S = sum of the reference's nucleotide values mod 4

S matters because dna_transform's recurrence
    c_i = (p_i + r_{i mod L} + c_{i-1}) mod 4
is a running (prefix) sum: c_i = (sum_{j<=i} (p_j + r_{j mod L})) mod 4.
Since R_{i+L} = (R_i + S) mod 4 for the accumulated reference
contribution, the mask that gets added to the plaintream repeats with
period L when S = 0 (mod 4), and with a longer period (2L or 4L)
otherwise. S = 0 reproduces exactly the kind of periodicity the
feedback term was introduced to remove (Section 6.2's tiled-mask design,
rejected for a lag-L autocorrelation of 0.835).

This script crosses base balance and S mod 4 in a 2x2 design (cells
A-D below) to separate their effects on the post_dna entropy gap,
instead of leaving them confounded as they were in Section 7.4's
two-sequence comparison.

Cells (all L=61, matching the real reference sequence's length):

    cell | composition        | balance  | S   | S mod 4
    -----|---------------------|----------|-----|--------
    A    | A15 T16 C15 G15     | balanced | 91  | 3   (= the real sequence's cell)
    B    | A15 T15 C16 G15     | balanced | 92  | 0
    C    | A20 T16 C16 G9      | skewed   | 75  | 3
    D    | A20 T15 C17 G9      | skewed   | 76  | 0

For each cell, 20 random permutations of that exact multiset are
generated (fixed, recorded seeds), plus, for cell A only, one extra,
21st case using the real reference sequence in its real order
(reference_id "A_real"), so the result ties back to Table 7.1.

For each of the resulting 81 reference sequences, Pipeline A's DNA
stage only is run (dna_transform, no AES-GCM, no key) over the three
small frozen corpus files, and entropy, chi-square, and lag-L
autocorrelation are measured at post_dna, reusing src/metrics.py's
functions unmodified.

--------------------------------------------------------------------
Deviation from the task spec: the autocorrelation metric
--------------------------------------------------------------------
The task spec asks, if an M1-era script defining the original 0.835 /
-0.008 / 0.017 figures (Section 6.2) still exists, to reuse *its*
definition instead, for comparability. That script exists:
scripts/measure_entropy_periodicity.py. Its actual metric is NOT a
Pearson autocorrelation. It is a lag-`period_bytes` XOR-preservation
ratio computed on raw ciphertext/plaintext BYTES:
    preserved_ratio = fraction of i where
        cipher[i] XOR cipher[i+period_bytes] == plain[i] XOR plain[i+period_bytes]
with period_bytes = len(reference_sequence) // 4 (an integer number of
bytes, since 4 nucleotides pack into 1 byte).

That definition cannot be reused unmodified here: it requires the
reference length to be a multiple of 4 nucleotides so period_bytes is
an integer. All four cells here use L=61, which is not a multiple of 4
(61 / 4 = 15.25). Forcing an integer byte lag (e.g. rounding to 15)
would measure a different, arbitrary lag, not lag-L, and would silently
misrepresent what "lag L" means for this experiment.

Resolution taken here: autocorrelation is instead measured as a Pearson
correlation between the post_dna NUCLEOTIDE-VALUE sequence and itself
shifted by L nucleotides (nt[:-L] vs nt[L:]), reusing
src/metrics.py's pearson_correlation() unmodified (fed nucleotide
values packed as a byte array, one value 0-3 per byte -- a legitimate
input to that function, which only cares about equal-length byte
arrays). This is a DIFFERENT metric, at nucleotide-level lag instead of
byte-level lag, from the one behind Section 6.2's 0.835 / -0.008 / 0.017
figures. The two are only qualitatively comparable (near 0 = no leak,
large magnitude = leak); the new autocorr_lag_L numbers reported here
are NOT directly numerically comparable to Section 6.2's numbers, and
should not be presented as if they were.

Run from the `project/` directory:
    python3 scripts/measure_reference_sequence_factorial.py
"""

import csv
import hashlib
import os
import random
import statistics
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from dna_transform import DEFAULT_MAPPING, dna_transform  # noqa: E402
from dna_codec import bytes_to_bits, bits_to_dna  # noqa: E402
from metrics import chi_square_uniform, pearson_correlation, shannon_entropy  # noqa: E402

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
CORPUS_DIR = os.path.join(DATA_DIR, "corpus")
RESULTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "results"))
OUTPUT_CSV = os.path.join(RESULTS_DIR, "reference_sequence_factorial.csv")

NT_TO_VAL = {nt: int(bits, 2) for bits, nt in DEFAULT_MAPPING.items()}

N_PERMUTATIONS = 20
L = 61

CELLS = {
    "A": {"A": 15, "T": 16, "C": 15, "G": 15},
    "B": {"A": 15, "T": 15, "C": 16, "G": 15},
    "C": {"A": 20, "T": 16, "C": 16, "G": 9},
    "D": {"A": 20, "T": 15, "C": 17, "G": 9},
}
CELL_BALANCE = {"A": "balanced", "B": "balanced", "C": "skewed", "D": "skewed"}

CORPUS_FILES = {
    "text": "text_small.txt",
    "json": "json_small.json",
    "random": "random_small.bin",
}

# Distinct, non-overlapping seed ranges per cell so every (cell, index)
# pair maps to one fixed, recorded, reproducible seed.
SEED_BASE = {"A": 1000, "B": 2000, "C": 3000, "D": 4000}


def _composition_string(comp: dict) -> str:
    return "".join(f"{base}{comp[base]}" for base in "ATCG")


def _s_mod_4(comp: dict) -> int:
    # S = n_T*1 + n_C*2 + n_G*3 (mod 4); A contributes 0 (value 0 under
    # the A=0/T=1/C=2/G=3 mapping).
    s = comp["T"] * 1 + comp["C"] * 2 + comp["G"] * 3
    return s % 4


def _verify_cells():
    expected_s_mod_4 = {"A": 3, "B": 0, "C": 3, "D": 0}
    for cell, comp in CELLS.items():
        total = sum(comp.values())
        assert total == 61, f"cell {cell}: composition sums to {total}, expected 61"
        s_mod_4 = _s_mod_4(comp)
        assert s_mod_4 == expected_s_mod_4[cell], (
            f"cell {cell}: S mod 4 = {s_mod_4}, expected {expected_s_mod_4[cell]}"
        )


def _verify_checksums():
    manifest_path = os.path.join(CORPUS_DIR, "CHECKSUMS.sha256")
    with open(manifest_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            expected_hash, filename = line.split(maxsplit=1)
            filename = filename.strip()
            path = os.path.join(CORPUS_DIR, filename)
            with open(path, "rb") as fh:
                actual_hash = hashlib.sha256(fh.read()).hexdigest()
            assert actual_hash == expected_hash, (
                f"checksum mismatch for {filename}: expected {expected_hash}, got {actual_hash}"
            )


def _load_corpus_file(name: str) -> bytes:
    with open(os.path.join(CORPUS_DIR, name), "rb") as f:
        return f.read()


def _load_real_reference() -> str:
    with open(os.path.join(DATA_DIR, "reference_sequence.txt")) as f:
        return f.read().strip().upper()


def _shuffled_sequence(comp: dict, seed: int) -> str:
    chars = list("".join(base * comp[base] for base in "ATCG"))
    rng = random.Random(seed)
    rng.shuffle(chars)
    return "".join(chars)


def _nucleotide_value_bytes(data: bytes) -> bytes:
    """
    Nucleotide-value sequence of `data`'s DNA representation, as a bytes
    object (one value 0-3 per element) so it can be fed directly into
    src/metrics.py's pearson_correlation() unmodified.
    """
    dna = bits_to_dna(bytes_to_bits(data), DEFAULT_MAPPING)
    return bytes(NT_TO_VAL[ch] for ch in dna)


def _autocorr_lag_L(post_dna_bytes: bytes, lag: int) -> float:
    nt_vals = _nucleotide_value_bytes(post_dna_bytes)
    if len(nt_vals) <= lag:
        return float("nan")
    return pearson_correlation(nt_vals[:-lag], nt_vals[lag:])


def _measure_one_reference(reference_sequence: str, corpus: dict) -> dict:
    """Returns {data_class: {"entropy":..., "chisq":..., "autocorr":...}}."""
    result = {}
    for data_class, data in corpus.items():
        post_dna = dna_transform(data, reference_sequence)
        result[data_class] = {
            "entropy": shannon_entropy(post_dna),
            "chisq": chi_square_uniform(post_dna),
            "autocorr": _autocorr_lag_L(post_dna, L),
        }
    return result


def run():
    _verify_cells()
    _verify_checksums()

    corpus = {name: _load_corpus_file(fname) for name, fname in CORPUS_FILES.items()}
    real_reference = _load_real_reference()
    assert len(real_reference) == L, f"real reference length {len(real_reference)} != {L}"

    rows = []

    references = []  # list of (reference_id, cell, ref_seq, permutation_seed)
    for cell, comp in CELLS.items():
        for i in range(N_PERMUTATIONS):
            seed = SEED_BASE[cell] + i
            ref_seq = _shuffled_sequence(comp, seed)
            references.append((f"{cell}_{i}", cell, ref_seq, seed))
    references.append(("A_real", "A", real_reference, None))

    print(f"Measuring {len(references)} reference sequences x {len(corpus)} files ...")
    per_reference_metrics = {}
    for reference_id, cell, ref_seq, seed in references:
        per_reference_metrics[reference_id] = _measure_one_reference(ref_seq, corpus)
        print(f"  {reference_id} (cell {cell}, seed={seed}) done")

    for reference_id, cell, ref_seq, seed in references:
        comp = CELLS[cell]
        metrics_by_class = per_reference_metrics[reference_id]
        entropy_gap_text = metrics_by_class["random"]["entropy"] - metrics_by_class["text"]["entropy"]
        entropy_gap_json = metrics_by_class["random"]["entropy"] - metrics_by_class["json"]["entropy"]

        for data_class, file_name in CORPUS_FILES.items():
            m = metrics_by_class[data_class]
            rows.append(
                {
                    "reference_id": reference_id,
                    "cell": cell,
                    "composition": _composition_string(comp),
                    "balance": CELL_BALANCE[cell],
                    "s_mod_4": _s_mod_4(comp),
                    "permutation_seed": seed if seed is not None else "",
                    "data_class": data_class,
                    "file": file_name,
                    "entropy_post_dna": m["entropy"],
                    "chisq_post_dna": m["chisq"],
                    "autocorr_lag_L": m["autocorr"],
                    "entropy_gap_text": entropy_gap_text,
                    "entropy_gap_json": entropy_gap_json,
                }
            )

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "reference_id",
                "cell",
                "composition",
                "balance",
                "s_mod_4",
                "permutation_seed",
                "data_class",
                "file",
                "entropy_post_dna",
                "chisq_post_dna",
                "autocorr_lag_L",
                "entropy_gap_text",
                "entropy_gap_json",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    print(f"\nWrote {len(rows)} rows to {OUTPUT_CSV}")

    # --- Summary table: mean +/- sd across the 20 permutations per cell ---
    print("\n=== Summary (mean +/- sd across 20 permutations; A_real excluded) ===")
    print(f"{'cell':5s} {'balance':9s} {'S mod4':7s} {'gap(text)':16s} {'chisq(text)':18s} {'autocorr(text)':16s}")
    summary_rows = []
    for cell in ("A", "B", "C", "D"):
        gaps = [
            r["entropy_gap_text"] for r in rows
            if r["cell"] == cell and r["reference_id"] != "A_real" and r["data_class"] == "text"
        ]
        chisqs = [
            r["chisq_post_dna"] for r in rows
            if r["cell"] == cell and r["reference_id"] != "A_real" and r["data_class"] == "text"
        ]
        autocorrs = [
            r["autocorr_lag_L"] for r in rows
            if r["cell"] == cell and r["reference_id"] != "A_real" and r["data_class"] == "text"
        ]
        gap_mean, gap_sd = statistics.mean(gaps), statistics.stdev(gaps)
        chisq_mean, chisq_sd = statistics.mean(chisqs), statistics.stdev(chisqs)
        ac_mean, ac_sd = statistics.mean(autocorrs), statistics.stdev(autocorrs)
        print(
            f"{cell:5s} {CELL_BALANCE[cell]:9s} {_s_mod_4(CELLS[cell]):<7d} "
            f"{gap_mean:.4f}+/-{gap_sd:.4f}   {chisq_mean:9.2f}+/-{chisq_sd:7.2f}   "
            f"{ac_mean:+.4f}+/-{ac_sd:.4f}"
        )
        summary_rows.append(
            (cell, CELL_BALANCE[cell], _s_mod_4(CELLS[cell]), gap_mean, gap_sd, chisq_mean, chisq_sd, ac_mean, ac_sd)
        )

    real_row = [r for r in rows if r["reference_id"] == "A_real" and r["data_class"] == "text"][0]
    print(
        f"\nA_real (real sequence, real order): gap(text)={real_row['entropy_gap_text']:.4f}  "
        f"chisq(text)={real_row['chisq_post_dna']:.3f}  autocorr(text)={real_row['autocorr_lag_L']:+.4f}"
    )

    return summary_rows


if __name__ == "__main__":
    run()
