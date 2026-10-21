"""
scripts/summarize_reference_sequence_factorial.py

Statistical summary of results/reference_sequence_factorial.csv (produced
by scripts/measure_reference_sequence_factorial.py): per-cell mean/sd for
entropy gap, chi-square, and lag-L autocorrelation, two-sample t-statistics
isolating the balance effect (A vs C, B vs D) and the S-mod-4 effect
(A vs B, C vs D), and a z-score comparing the real reference sequence's
own gap/chi-square against its cell's (A's) permutation distribution.

Run from the `project/` directory, after measure_reference_sequence_factorial.py:
    python3 scripts/summarize_reference_sequence_factorial.py
"""

import csv
import math
import os
import statistics

RESULTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "results"))
INPUT_CSV = os.path.join(RESULTS_DIR, "reference_sequence_factorial.csv")


def _load_rows():
    with open(INPUT_CSV) as f:
        return list(csv.DictReader(f))


def _vals(rows, cell, metric, data_class="text", exclude_real=True):
    return [
        float(r[metric])
        for r in rows
        if r["cell"] == cell
        and r["data_class"] == data_class
        and not (exclude_real and r["reference_id"] == "A_real")
    ]


def _two_sample_t(a, b):
    ma, mb = statistics.mean(a), statistics.mean(b)
    sa, sb = statistics.stdev(a), statistics.stdev(b)
    n = len(a)
    se = math.sqrt(sa**2 / n + sb**2 / n)
    return (ma - mb) / se, ma - mb, se


def run():
    rows = _load_rows()

    print("=== Per-cell mean +/- sd across 20 permutations (text data class) ===")
    for metric in ("entropy_gap_text", "chisq_post_dna", "autocorr_lag_L"):
        print(f"--- {metric} ---")
        for cell in "ABCD":
            v = _vals(rows, cell, metric)
            print(f"  {cell}: mean={statistics.mean(v):.4f} sd={statistics.stdev(v):.4f} n={len(v)}")

    print("\n=== Balance effect (skewed vs balanced, holding S fixed) ===")
    for skewed, balanced in (("C", "A"), ("D", "B")):
        a = _vals(rows, skewed, "entropy_gap_text")
        b = _vals(rows, balanced, "entropy_gap_text")
        t, diff, se = _two_sample_t(a, b)
        print(f"  gap: {skewed} vs {balanced}: diff={diff:.4f} se={se:.4f} t={t:.2f}")

    print("\n=== S mod 4 effect (S=3 vs S=0, holding balance fixed) ===")
    for s3, s0 in (("A", "B"), ("C", "D")):
        a = _vals(rows, s3, "entropy_gap_text")
        b = _vals(rows, s0, "entropy_gap_text")
        t, diff, se = _two_sample_t(a, b)
        print(f"  gap: {s3} vs {s0}: diff={diff:.4f} se={se:.4f} t={t:.2f}")
        a = _vals(rows, s3, "autocorr_lag_L")
        b = _vals(rows, s0, "autocorr_lag_L")
        t, diff, se = _two_sample_t(a, b)
        print(f"  autocorr: {s3} vs {s0}: diff={diff:.4f} se={se:.4f} t={t:.2f}")

    print("\n=== Real reference sequence vs. its cell's (A's) permutation distribution ===")
    for metric in ("entropy_gap_text", "chisq_post_dna", "autocorr_lag_L"):
        perm_vals = _vals(rows, "A", metric)
        real_val = [
            float(r[metric]) for r in rows if r["reference_id"] == "A_real" and r["data_class"] == "text"
        ][0]
        m, s = statistics.mean(perm_vals), statistics.stdev(perm_vals)
        z = (real_val - m) / s if s > 0 else float("nan")
        print(f"  {metric}: A_real={real_val:.4f} vs cell-A perm mean={m:.4f} sd={s:.4f} -> z={z:.2f}")

    print("\n=== JSON data class: per-cell entropy_gap_json mean +/- sd ===")
    for cell in "ABCD":
        v = _vals(rows, cell, "entropy_gap_json", data_class="json")
        print(f"  {cell}: mean={statistics.mean(v):.4f} sd={statistics.stdev(v):.4f}")


if __name__ == "__main__":
    run()
