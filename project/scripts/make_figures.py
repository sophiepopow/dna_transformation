"""
scripts/make_figures.py

M6: generates the 3 required figures + 1 table from
results/experiment_results.csv (produced by scripts/run_experiment.py),
using matplotlib per the milestone spec.

Outputs (all under results/):
  - fig_entropy_by_stage.png            grouped bar, one group per data class
  - fig_avalanche_comparison.png        pipeline A vs. B avalanche_pct
  - fig_compression_ratio_by_stage.png  grouped bar, one group per data class
  - table_throughput_size_overhead.csv  per-(file, pipeline) throughput +
                                         both size-overhead conventions

Design notes:

- Values are averaged across the two corpus sizes (small/large) within
  each data class for the "by stage" bar charts, since the milestone spec
  asks for "one group per data class" (3 groups: text/json/random), not
  6 (per file). The small-vs-large difference is negligible for these
  metrics (see docs/findings.md / experiment_results.csv directly for the
  per-file numbers if a size breakdown is needed later).

- Bar colors use a fixed categorical hue order (never re-cycled per
  chart) so the same stage/series always gets the same color across
  figures, and every bar carries a direct numeric label -- this project's
  charts are static print/thesis figures (not an interactive light/dark
  HTML surface), so labeling every bar directly is the simplest way to
  keep values legible regardless of a slot's on-surface contrast.

- fig_avalanche_comparison.png deliberately shows THREE bars per data
  class, not two, because avalanche_pct means different things at
  different stages (see scripts/run_experiment.py's "Decision A"
  docstring section, and docs/raport.md's M4 section): Pipeline A's
  post_dna avalanche is the real, deterministic diffusion signal (~30%),
  while both pipelines' post_classical avalanche is dominated by
  AES-GCM's per-call random nonce (~50% for both, not evidence of the
  DNA transform's diffusion). Showing only "A vs. B" at one stage would
  either hide the real signal (if post_classical only) or misleadingly
  imply B has a comparable post_dna number (it has no DNA stage at all).
  The chart title and a caption-style subtitle make this explicit.

Run from the `project/` directory:
    /Users/sophiepopow/Documents/PK/master/dna/.venv/bin/python scripts/make_figures.py
"""

import os

import textwrap

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

RESULTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "results"))
CSV_PATH = os.path.join(RESULTS_DIR, "experiment_results.csv")

# Fixed categorical hues (dataviz skill's validated default palette,
# light-mode slots), assigned by role and never re-cycled within a chart.
BLUE = "#2a78d6"
ORANGE = "#eb6834"
AQUA = "#1baf7a"
VIOLET = "#4a3aa7"

DATA_CLASS_ORDER = ["text", "json", "random"]
DATA_CLASS_LABELS = {"text": "Text", "json": "JSON", "random": "Random"}

GRID_COLOR = "#d8d8d5"
TEXT_COLOR = "#333333"


def _load() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATH)
    df["data_class"] = pd.Categorical(df["data_class"], categories=DATA_CLASS_ORDER, ordered=True)
    return df


def _grouped_bar_by_stage(df: pd.DataFrame, value_col: str, ylabel: str, title: str, out_path: str):
    """
    Shared builder for the entropy/compression "by stage, grouped by data
    class" figures: 4 series (Input, Post-DNA [A], Post-Classical [A],
    Post-Classical [B]) averaged over small+large per data class.
    """
    series_defs = [
        ("Input", df[df["stage"] == "input"], BLUE),
        ("Post-DNA (A)", df[(df["pipeline"] == "A") & (df["stage"] == "post_dna")], ORANGE),
        ("Post-Classical (A)", df[(df["pipeline"] == "A") & (df["stage"] == "post_classical")], AQUA),
        ("Post-Classical (B)", df[(df["pipeline"] == "B") & (df["stage"] == "post_classical")], VIOLET),
    ]

    means = {}
    for label, subset, _color in series_defs:
        means[label] = subset.groupby("data_class", observed=True)[value_col].mean().reindex(DATA_CLASS_ORDER)

    n_series = len(series_defs)
    n_groups = len(DATA_CLASS_ORDER)
    bar_width = 0.8 / n_series
    x = range(n_groups)

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.set_axisbelow(True)
    ax.yaxis.grid(True, color=GRID_COLOR, linewidth=0.8)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)

    for i, (label, _subset, color) in enumerate(series_defs):
        offsets = [xi + (i - (n_series - 1) / 2) * bar_width for xi in x]
        values = means[label].values
        bars = ax.bar(offsets, values, width=bar_width * 0.92, label=label, color=color)
        for rect, v in zip(bars, values):
            ax.annotate(
                f"{v:.2f}",
                xy=(rect.get_x() + rect.get_width() / 2, rect.get_height()),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=7.5,
                color=TEXT_COLOR,
            )

    ax.set_xticks(list(x))
    ax.set_xticklabels([DATA_CLASS_LABELS[c] for c in DATA_CLASS_ORDER])
    ax.set_ylabel(ylabel, color=TEXT_COLOR)
    ax.set_xlabel("Data class", color=TEXT_COLOR)
    ax.set_title(title, color=TEXT_COLOR, fontsize=12, fontweight="bold")
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=4, fontsize=9)
    ax.tick_params(colors=TEXT_COLOR)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Wrote {out_path}")


def make_entropy_figure(df: pd.DataFrame):
    _grouped_bar_by_stage(
        df,
        value_col="entropy_bits_per_byte",
        ylabel="Shannon entropy (bits/byte)",
        title="Entropy by pipeline stage, per data class\n(averaged over small + large corpus files)",
        out_path=os.path.join(RESULTS_DIR, "fig_entropy_by_stage.png"),
    )


def make_compression_ratio_figure(df: pd.DataFrame):
    _grouped_bar_by_stage(
        df,
        value_col="compression_ratio",
        ylabel="gzip compression ratio (compressed / original size)",
        title="Compression ratio by pipeline stage, per data class\n(averaged over small + large corpus files)",
        out_path=os.path.join(RESULTS_DIR, "fig_compression_ratio_by_stage.png"),
    )


def make_avalanche_figure(df: pd.DataFrame):
    series_defs = [
        ("A: post_dna (real diffusion signal)", df[(df["pipeline"] == "A") & (df["stage"] == "post_dna")], ORANGE),
        (
            "A: post_classical (AES-GCM nonce-dominated)",
            df[(df["pipeline"] == "A") & (df["stage"] == "post_classical")],
            AQUA,
        ),
        (
            "B: post_classical (AES-GCM nonce-dominated)",
            df[(df["pipeline"] == "B") & (df["stage"] == "post_classical")],
            VIOLET,
        ),
    ]

    means = {}
    for label, subset, _color in series_defs:
        means[label] = (
            subset.groupby("data_class", observed=True)["avalanche_pct"].mean().reindex(DATA_CLASS_ORDER)
        )

    n_series = len(series_defs)
    n_groups = len(DATA_CLASS_ORDER)
    bar_width = 0.8 / n_series
    x = range(n_groups)

    fig, ax = plt.subplots(figsize=(10, 6.8))
    ax.set_axisbelow(True)
    ax.yaxis.grid(True, color=GRID_COLOR, linewidth=0.8)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.axhline(50.0, color="#999999", linewidth=1.0, linestyle="--", zorder=0)

    for i, (label, _subset, color) in enumerate(series_defs):
        offsets = [xi + (i - (n_series - 1) / 2) * bar_width for xi in x]
        values = means[label].values
        bars = ax.bar(offsets, values, width=bar_width * 0.92, label=label, color=color)
        for rect, v in zip(bars, values):
            ax.annotate(
                f"{v:.1f}%",
                xy=(rect.get_x() + rect.get_width() / 2, rect.get_height()),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8,
                color=TEXT_COLOR,
            )

    ax.set_xticks(list(x))
    ax.set_xticklabels([DATA_CLASS_LABELS[c] for c in DATA_CLASS_ORDER])
    ax.set_ylabel("Avalanche effect (% bits flipped)", color=TEXT_COLOR)
    ax.set_xlabel("Data class", color=TEXT_COLOR)
    ax.set_ylim(0, 65)
    subtitle = (
        "Dashed line = ideal 50%. post_classical bars reflect AES-GCM's random nonce, "
        "not DNA-transform diffusion (see docs/raport.md, M4 section)."
    )
    wrapped_subtitle = "\n".join(textwrap.wrap(subtitle, width=62))
    ax.set_title(
        "Avalanche effect: Pipeline A vs. Pipeline B, by stage\n" + wrapped_subtitle,
        color=TEXT_COLOR,
        fontsize=10.5,
        fontweight="bold",
    )
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=1, fontsize=9)
    ax.tick_params(colors=TEXT_COLOR)

    fig.tight_layout()
    out_path = os.path.join(RESULTS_DIR, "fig_avalanche_comparison.png")
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Wrote {out_path}")


def make_throughput_size_overhead_table(df: pd.DataFrame):
    final_stage = df[df["stage"] == "post_classical"].copy()
    final_stage = final_stage.sort_values(["data_class", "size_class", "pipeline"])
    out = final_stage[
        [
            "file",
            "data_class",
            "size_class",
            "pipeline",
            "input_size_bytes",
            "total_ms",
            "throughput_bytes_per_sec",
            "size_overhead_body_pct",
            "size_overhead_full_aead_pct",
        ]
    ]
    out_path = os.path.join(RESULTS_DIR, "table_throughput_size_overhead.csv")
    out.to_csv(out_path, index=False)
    print(f"Wrote {out_path}")


def main():
    df = _load()
    make_entropy_figure(df)
    make_compression_ratio_figure(df)
    make_avalanche_figure(df)
    make_throughput_size_overhead_table(df)


if __name__ == "__main__":
    main()
