#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
論文用図表生成スクリプト v2
==========================
既存の分析結果（artifacts/analysis/）を読み込み、
論文用のPNG図表・LaTeXテーブルを reports/paper_figs_v2/ に出力する。

Usage:
    python scripts/paper_figs/gen_paper_figs_v2.py
    python scripts/paper_figs/gen_paper_figs_v2.py --out_dir reports/paper_figs_v2
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import NamedTuple

import numpy as np
import pandas as pd

try:
    from scripts.paper_figs.feature_definitions import get_explanatory_features
except ModuleNotFoundError:
    from feature_definitions import get_explanatory_features  # type: ignore[import-untyped]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TRAITS = ["C", "A", "E", "N", "O"]
TEACHERS = ["sonnet", "qwen3-235b", "gpt-oss-120b", "deepseek-v3"]
TEACHER_DISPLAY = {
    "sonnet": "Sonnet4",
    "qwen3-235b": "Qwen3-235B",
    "gpt-oss-120b": "GPT-OSS-120B",
    "deepseek-v3": "DeepSeek-V3",
}

FEATURE_COLUMNS = [
    "PG_speech_ratio", "PG_pause_mean", "PG_pause_p50", "PG_pause_p90",
    "PG_resp_gap_mean", "PG_resp_gap_p50", "PG_resp_gap_p90",
    "FILL_has_any", "FILL_rate_per_100chars",
    "IX_oirmarker_rate", "IX_oirmarker_after_question_rate",
    "IX_yesno_rate", "IX_yesno_after_question_rate",
    "IX_lex_overlap_mean", "IX_topic_drift_mean",
    "RESP_NE_AIZUCHI_RATE", "RESP_NE_ENTROPY", "RESP_YO_ENTROPY",
]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
class PermutationResult(NamedTuple):
    """Parsed permutation test result."""
    r_obs: float
    p_value: float


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser with 4 required/defaulted arguments."""
    ap = argparse.ArgumentParser(
        description="論文用図表生成スクリプト v2 — 既存分析結果から図表を生成",
    )
    ap.add_argument(
        "--results_dir",
        type=str,
        default="artifacts/analysis/results",
        help="Permutation結果ディレクトリ (default: artifacts/analysis/results)",
    )
    ap.add_argument(
        "--bootstrap_dir",
        type=str,
        default="artifacts/analysis/results/bootstrap",
        help="Bootstrap結果ディレクトリ (default: artifacts/analysis/results/bootstrap)",
    )
    ap.add_argument(
        "--features_parquet",
        type=str,
        default="artifacts/analysis/features_min/features_cejc_home2_hq1.parquet",
        help="特徴量parquetファイル (default: artifacts/analysis/features_min/features_cejc_home2_hq1.parquet)",
    )
    ap.add_argument(
        "--metadata_tsv",
        type=str,
        default=None,
        help="コーパス基本情報TSV（性別・年齢等）。未指定時はメタデータ関連図の生成をスキップ",
    )
    ap.add_argument(
        "--out_dir",
        type=str,
        default="reports/paper_figs_v2",
        help="出力ディレクトリ (default: reports/paper_figs_v2)",
    )
    return ap


# ---------------------------------------------------------------------------
# Permutation log parser
# ---------------------------------------------------------------------------
_RE_R_OBS = re.compile(r"r_obs\s*=\s*([0-9eE.+\-]+)")
_RE_P_VALUE = re.compile(r"p\(\|r\|\)\s*=\s*([0-9eE.+\-]+)")


def parse_permutation_log(path: str | Path) -> PermutationResult:
    """Parse a permutation.log file and extract r_obs and p(|r|).

    Parameters
    ----------
    path : str or Path
        Path to the permutation.log file.

    Returns
    -------
    PermutationResult
        Named tuple with r_obs and p_value.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.  The error message includes the path
        and the expected file format.
    ValueError
        If the file cannot be parsed (missing r_obs or p(|r|)).
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"permutation.log not found: {p}\n"
            f"Expected format:\n"
            f"  alpha=100.0\n"
            f"  r_obs=0.434\n"
            f"  p(|r|)=0.0008  (n_perm=5000)"
        )
    text = p.read_text(encoding="utf-8")
    m_r = _RE_R_OBS.search(text)
    m_p = _RE_P_VALUE.search(text)
    if m_r is None or m_p is None:
        raise ValueError(
            f"Failed to parse permutation.log: {p}\n"
            f"Could not extract {'r_obs' if m_r is None else 'p(|r|)'}\n"
            f"Expected format:\n"
            f"  alpha=100.0\n"
            f"  r_obs=0.434\n"
            f"  p(|r|)=0.0008  (n_perm=5000)"
        )
    return PermutationResult(
        r_obs=float(m_r.group(1)),
        p_value=float(m_p.group(1)),
    )


# ---------------------------------------------------------------------------
# Bootstrap summary reader
# ---------------------------------------------------------------------------
BOOTSTRAP_EXPECTED_COLUMNS = [
    "feature", "coef_mean", "coef_std", "coef_q05", "coef_q95",
    "sign_mean", "sign_agree_rate", "topk_rate",
]


def read_bootstrap_summary(path: str | Path) -> pd.DataFrame:
    """Read a bootstrap_summary.tsv file.

    Parameters
    ----------
    path : str or Path
        Path to the bootstrap_summary.tsv file.

    Returns
    -------
    pd.DataFrame
        DataFrame with bootstrap summary columns.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.  The error message includes the path
        and the expected schema.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"bootstrap_summary.tsv not found: {p}\n"
            f"Expected columns: {', '.join(BOOTSTRAP_EXPECTED_COLUMNS)}"
        )
    df = pd.read_csv(p, sep="\t")
    return df


# ---------------------------------------------------------------------------
# Features parquet reader
# ---------------------------------------------------------------------------
def read_features_parquet(path: str | Path) -> pd.DataFrame:
    """Read the features parquet file and validate expected columns.

    Parameters
    ----------
    path : str or Path
        Path to the features parquet file.

    Returns
    -------
    pd.DataFrame
        DataFrame with feature columns.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.  The error message includes the path
        and the expected feature columns.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"Features parquet not found: {p}\n"
            f"Expected columns: {', '.join(FEATURE_COLUMNS)}"
        )
    df = pd.read_parquet(p)
    return df


# ---------------------------------------------------------------------------
# Metadata (corpus basic info) loader
# ---------------------------------------------------------------------------
METADATA_EXPECTED_COLUMNS = ["gender", "age"]


def load_metadata(path: str | Path) -> pd.DataFrame | None:
    """Load corpus metadata TSV (gender, age, etc.).

    Parameters
    ----------
    path : str or Path
        Path to the metadata TSV file.

    Returns
    -------
    pd.DataFrame or None
        DataFrame with available metadata columns, or *None* if the file
        does not exist (a warning is printed to stderr in that case).

    Notes
    -----
    - If the file is missing, a warning is emitted and ``None`` is returned
      so that downstream metadata-related figures can be skipped while other
      figure generation continues.
    - If expected columns (gender, age) are partially missing, only the
      available columns are retained and a warning lists the missing ones.
    """
    p = Path(path)
    if not p.exists():
        print(
            f"WARNING: metadata TSV not found: {p} — "
            f"メタデータ関連図の生成をスキップします",
            file=sys.stderr,
        )
        return None

    try:
        df = pd.read_csv(p, sep="\t", encoding="utf-8")
    except Exception as exc:
        print(
            f"WARNING: metadata TSV の読み込みに失敗: {p} — {exc}",
            file=sys.stderr,
        )
        return None

    # Check for expected columns; warn about missing ones
    missing = [c for c in METADATA_EXPECTED_COLUMNS if c not in df.columns]
    if missing:
        print(
            f"WARNING: metadata TSV に期待カラムが不足: {missing} — "
            f"利用可能なカラムのみで処理します (available: {list(df.columns)})",
            file=sys.stderr,
        )

    return df


# ---------------------------------------------------------------------------
# Teacher correlation reader
# ---------------------------------------------------------------------------
def read_teacher_corr(path: str | Path) -> pd.DataFrame:
    """Read a teacher correlation TSV (4×4 matrix).

    Parameters
    ----------
    path : str or Path
        Path to teacher_corr_{trait}.tsv.

    Returns
    -------
    pd.DataFrame
        4×4 correlation matrix with teacher names as index and columns.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"Teacher correlation TSV not found: {p}\n"
            f"Expected: 4×4 matrix with teachers as rows/columns"
        )
    df = pd.read_csv(p, sep="\t", index_col=0)
    return df


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------
def permutation_log_path(results_dir: str | Path, trait: str, teacher: str) -> Path:
    """Build the path to a permutation.log file."""
    return (
        Path(results_dir)
        / f"cejc_home2_hq1_{trait}only_{teacher}_controls_excluded"
        / "permutation.log"
    )


def bootstrap_summary_path(bootstrap_dir: str | Path, trait: str, teacher: str) -> Path:
    """Build the path to a bootstrap_summary.tsv file."""
    return (
        Path(bootstrap_dir)
        / f"cejc_home2_hq1_{trait}only_{teacher}_controls_excluded"
        / "bootstrap_summary.tsv"
    )


def teacher_corr_path(trait: str) -> Path:
    """Build the path to a teacher correlation TSV."""
    return Path("docs/homework/assets") / f"teacher_corr_{trait}.tsv"


# ---------------------------------------------------------------------------
# Placeholder stubs for figure/table generation (Tasks 1.3–1.8)
# ---------------------------------------------------------------------------
def gen_fig_permutation_C_bar(results_dir: Path, out_dir: Path) -> None:
    """Generate permutation bar chart for Conscientiousness (4 teachers)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    trait = "C"
    teachers_disp, r_obs_vals, p_vals = [], [], []
    for teacher in TEACHERS:
        res = parse_permutation_log(permutation_log_path(results_dir, trait, teacher))
        teachers_disp.append(TEACHER_DISPLAY[teacher])
        r_obs_vals.append(res.r_obs)
        p_vals.append(res.p_value)

    fig, ax = plt.subplots(figsize=(6, 4))
    colors = ["#2166ac" if p < 0.05 else "#b2182b" for p in p_vals]
    bars = ax.bar(range(len(teachers_disp)), r_obs_vals, color=colors, width=0.55,
                  edgecolor="white", linewidth=0.8)
    for bar, p in zip(bars, p_vals):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.008,
                f"p={p:.4f}", ha="center", va="bottom", fontsize=9)
    ax.legend(handles=[
        Patch(facecolor="#2166ac", edgecolor="white", label="p < 0.05"),
        Patch(facecolor="#b2182b", edgecolor="white", label="p >= 0.05"),
    ], loc="upper right", fontsize=10, framealpha=0.9)
    ax.set_xticks(range(len(teachers_disp)))
    ax.set_xticklabels(teachers_disp, fontsize=10)
    ax.set_ylabel("Observed correlation ($r_{obs}$)", fontsize=12)
    ax.set_title("Permutation Test: Conscientiousness (C)", fontsize=13, pad=10)
    ax.set_ylim(0, max(r_obs_vals) * 1.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(out_dir / "fig_permutation_C_bar.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def gen_fig_ensemble_permutation(results_dir: Path, out_dir: Path) -> None:
    """Generate ensemble 5-trait Permutation results bar chart (fig_ensemble_permutation.png).

    Reads ensemble_summary.tsv from results_dir and draws a bar chart with
    5 bars (O, C, E, A, N) showing r_obs values.  Bars are coloured by
    significance: blue (#2166ac) for p < 0.05, red (#b2182b) otherwise.
    Each bar is annotated with its p-value.

    Parameters
    ----------
    results_dir : Path
        Directory containing ``ensemble_summary.tsv``
        (columns: trait, r_obs, p_value).
    out_dir : Path
        Directory where fig_ensemble_permutation.png will be saved.

    Raises
    ------
    FileNotFoundError
        If ensemble_summary.tsv does not exist.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    summary_path = results_dir / "ensemble_summary.tsv"
    if not summary_path.exists():
        raise FileNotFoundError(
            f"ensemble_summary.tsv not found: {summary_path}\n"
            f"Expected columns: trait, r_obs, p_value"
        )

    df = pd.read_csv(summary_path, sep="\t")

    # Ensure expected trait order: O, C, E, A, N
    trait_order = ["O", "C", "E", "A", "N"]
    df = df.set_index("trait").loc[trait_order].reset_index()

    traits = df["trait"].tolist()
    r_obs_vals = df["r_obs"].tolist()
    p_vals = df["p_value"].tolist()

    fig, ax = plt.subplots(figsize=(6, 4))
    colors = ["#2166ac" if p < 0.05 else "#b2182b" for p in p_vals]
    bars = ax.bar(range(len(traits)), r_obs_vals, color=colors, width=0.55,
                  edgecolor="white", linewidth=0.8)

    for bar, p in zip(bars, p_vals):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.008,
                f"p={p:.4f}", ha="center", va="bottom", fontsize=9)

    ax.legend(handles=[
        Patch(facecolor="#2166ac", edgecolor="white", label="p < 0.05"),
        Patch(facecolor="#b2182b", edgecolor="white", label="p >= 0.05"),
    ], loc="upper right", fontsize=10, framealpha=0.9)

    ax.set_xticks(range(len(traits)))
    ax.set_xticklabels(traits, fontsize=12)
    ax.set_ylabel("Observed correlation ($r_{obs}$)", fontsize=12)
    ax.set_title("Ensemble Permutation Test: Big Five (5 Traits)", fontsize=13, pad=10)
    ax.set_ylim(0, max(r_obs_vals) * 1.25 if max(r_obs_vals) > 0 else 0.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.tight_layout()
    fig.savefig(out_dir / "fig_ensemble_permutation.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def gen_fig_baseline_vs_extended(results_dir: Path, out_dir: Path) -> None:
    """Generate baseline vs extended model comparison figure (fig_baseline_vs_extended.png).

    Reads all ``baseline_vs_extended_*.tsv`` files from *results_dir* and
    draws a grouped bar chart comparing r_baseline (Classical 9 features)
    vs r_extended (all 18 features) for each Big Five trait (O, C, E, A, N).
    Δr is annotated above each pair.

    If multiple teachers exist for the same trait, values are averaged
    across teachers.

    Parameters
    ----------
    results_dir : Path
        Directory containing ``baseline_vs_extended_*.tsv`` files
        (columns: trait, teacher, r_baseline, p_baseline, r_extended,
        p_extended, delta_r).
    out_dir : Path
        Directory where fig_baseline_vs_extended.png will be saved.

    Raises
    ------
    FileNotFoundError
        If no baseline_vs_extended_*.tsv files are found.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # --- Collect all TSV files ---
    tsv_files = sorted(results_dir.glob("baseline_vs_extended_*.tsv"))
    if not tsv_files:
        raise FileNotFoundError(
            f"No baseline_vs_extended_*.tsv files found in: {results_dir}\n"
            f"Expected columns: trait, teacher, r_baseline, p_baseline, "
            f"r_extended, p_extended, delta_r"
        )

    # --- Read and concatenate ---
    frames = [pd.read_csv(f, sep="\t") for f in tsv_files]
    df = pd.concat(frames, ignore_index=True)

    # --- Average across teachers per trait ---
    trait_order = ["O", "C", "E", "A", "N"]
    agg = (
        df.groupby("trait")[["r_baseline", "r_extended", "delta_r"]]
        .mean()
    )

    # Ensure trait order; skip missing traits
    traits = [t for t in trait_order if t in agg.index]
    r_base = [agg.loc[t, "r_baseline"] for t in traits]
    r_ext = [agg.loc[t, "r_extended"] for t in traits]
    delta = [agg.loc[t, "delta_r"] for t in traits]

    # --- Draw grouped bar chart ---
    x = np.arange(len(traits))
    width = 0.32

    fig, ax = plt.subplots(figsize=(7, 4.5))
    bars_base = ax.bar(
        x - width / 2, r_base, width,
        label="Baseline (Classical 9)",
        color="#92c5de", edgecolor="white", linewidth=0.8,
    )
    bars_ext = ax.bar(
        x + width / 2, r_ext, width,
        label="Extended (All 18)",
        color="#2166ac", edgecolor="white", linewidth=0.8,
    )

    # --- Annotate Δr above each pair ---
    for i in range(len(traits)):
        pair_max = max(r_base[i], r_ext[i])
        dr = delta[i]
        sign = "+" if dr >= 0 else ""
        ax.text(
            x[i], pair_max + 0.015,
            f"Δr={sign}{dr:.3f}",
            ha="center", va="bottom", fontsize=9, fontstyle="italic",
        )

    ax.set_xticks(x)
    ax.set_xticklabels(traits, fontsize=12)
    ax.set_ylabel("Observed correlation ($r_{obs}$)", fontsize=12)
    ax.set_title(
        "Baseline (Classical 9) vs Extended (All 18) Model Comparison",
        fontsize=13, pad=10,
    )
    y_max = max(max(r_base), max(r_ext)) if traits else 0.5
    ax.set_ylim(0, y_max * 1.35)
    ax.legend(loc="upper right", fontsize=10, framealpha=0.9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.tight_layout()
    fig.savefig(out_dir / "fig_baseline_vs_extended.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def gen_fig_bootstrap_C_radar(bootstrap_dir: Path, out_dir: Path) -> None:
    """Generate bootstrap radar chart for C (Sonnet4 teacher). [Task 1.4]

    Reads bootstrap_summary.tsv for trait=C, teacher=sonnet, selects the
    Top 10 features by topk_rate (descending), and draws a radar/spider
    chart with two overlaid metrics: topk_rate and sign_agree_rate.

    Parameters
    ----------
    bootstrap_dir : Path
        Root directory containing bootstrap result sub-directories.
    out_dir : Path
        Directory where fig_bootstrap_C_radar.png will be saved.
    """
    import matplotlib.pyplot as plt

    # --- Read data ---
    tsv_path = bootstrap_summary_path(bootstrap_dir, trait="C", teacher="sonnet")
    df = read_bootstrap_summary(tsv_path)

    # --- Select Top 10 by topk_rate descending ---
    top10 = df.nlargest(10, "topk_rate").reset_index(drop=True)

    labels = top10["feature"].tolist()
    topk = top10["topk_rate"].values
    sign = top10["sign_agree_rate"].values

    n = len(labels)
    # Compute angle for each axis (evenly spaced, closing the polygon)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    angles += angles[:1]  # close the polygon

    topk_closed = np.concatenate([topk, topk[:1]])
    sign_closed = np.concatenate([sign, sign[:1]])

    # --- Draw radar chart ---
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))

    # topk_rate
    ax.plot(angles, topk_closed, "o-", linewidth=1.8, label="Top-K Rate", color="#2176AE")
    ax.fill(angles, topk_closed, alpha=0.15, color="#2176AE")

    # sign_agree_rate
    ax.plot(angles, sign_closed, "s--", linewidth=1.8, label="Sign Agree Rate", color="#D7263D")
    ax.fill(angles, sign_closed, alpha=0.10, color="#D7263D")

    # --- Axis labels ---
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=9)

    # Radial ticks
    ax.set_ylim(0, 1.0)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(["0.2", "0.4", "0.6", "0.8", "1.0"], fontsize=8, color="grey")

    ax.set_title(
        "Bootstrap Stability: Top-10 Features for C (Sonnet4)",
        fontsize=12,
        fontweight="bold",
        pad=24,
    )
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.10), fontsize=10)

    fig.tight_layout()
    out_path = out_dir / "fig_bootstrap_C_radar.png"
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def gen_fig_teacher_heatmap(out_dir: Path) -> None:
    """Generate teacher agreement heatmap (5 traits × 4 teachers). [Task 1.5]

    For each trait, reads the 4×4 teacher Pearson correlation matrix and
    computes per-teacher mean r (average of that teacher's off-diagonal
    correlations) and overall trait mean r (mean of upper-triangle
    off-diagonal elements).

    The output is a 5×4 heatmap (rows=traits, columns=teachers) with
    per-cell values and a right-side annotation column showing the overall
    trait mean r.

    Parameters
    ----------
    out_dir : Path
        Directory where fig_teacher_heatmap.png will be saved.
    """
    import matplotlib.pyplot as plt
    from matplotlib.colors import Normalize

    # --- Collect per-teacher mean r for each trait ---
    # TSV files use "sonnet4" but TEACHERS list uses "sonnet"; map accordingly
    tsv_teachers = ["sonnet4", "qwen3-235b", "deepseek-v3", "gpt-oss-120b"]

    data = np.zeros((len(TRAITS), len(TEACHERS)))  # 5 × 4
    trait_mean_r = []  # overall mean r per trait

    for i, trait in enumerate(TRAITS):
        corr_path = teacher_corr_path(trait)
        corr_df = read_teacher_corr(corr_path)

        # Extract the correlation matrix as numpy array (aligned to tsv_teachers order)
        mat = corr_df.loc[tsv_teachers, tsv_teachers].values

        # Overall trait mean r: mean of upper-triangle off-diagonal elements
        n_teachers = len(tsv_teachers)
        upper_vals = []
        for r in range(n_teachers):
            for c in range(r + 1, n_teachers):
                upper_vals.append(mat[r, c])
        trait_mean_r.append(np.mean(upper_vals))

        # Per-teacher mean r: mean of off-diagonal elements in that teacher's row
        for j in range(n_teachers):
            off_diag = [mat[j, k] for k in range(n_teachers) if k != j]
            data[i, j] = np.mean(off_diag)

    # --- Draw heatmap ---
    fig, ax = plt.subplots(figsize=(7.5, 4.0))

    norm = Normalize(vmin=0.3, vmax=0.8)
    im = ax.imshow(data, cmap="YlOrRd", aspect="auto", norm=norm)

    # Annotate each cell
    for i in range(len(TRAITS)):
        for j in range(len(TEACHERS)):
            val = data[i, j]
            text_color = "white" if val > 0.65 else "black"
            ax.text(j, i, f"{val:.3f}", ha="center", va="center",
                    fontsize=10, color=text_color, fontweight="medium")

    # Axis labels
    teacher_labels = [TEACHER_DISPLAY[t] for t in TEACHERS]
    ax.set_xticks(range(len(TEACHERS)))
    ax.set_xticklabels(teacher_labels, fontsize=10)
    ax.set_yticks(range(len(TRAITS)))
    ax.set_yticklabels(TRAITS, fontsize=12, fontweight="bold")

    # Annotate trait mean r on the right side
    for i, mr in enumerate(trait_mean_r):
        ax.text(len(TEACHERS) + 0.15, i, f"mean r = {mr:.3f}",
                ha="left", va="center", fontsize=9, fontstyle="italic",
                color="#333333")

    # Expand x-axis to make room for the mean r annotation
    ax.set_xlim(-0.5, len(TEACHERS) - 0.5 + 1.8)

    ax.set_title("Inter-Teacher Agreement (per-teacher mean r)",
                 fontsize=12, fontweight="bold", pad=12)
    ax.set_xlabel("Teacher (LLM)", fontsize=12)
    ax.set_ylabel("Trait", fontsize=12)

    # Colorbar
    cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
    cbar.set_label("Mean Pearson r", fontsize=10)

    fig.tight_layout()
    out_path = out_dir / "fig_teacher_heatmap.png"
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def gen_tab_descriptive_stats(features_parquet: Path, out_dir: Path) -> None:
    """Generate descriptive statistics LaTeX table. [Task 1.6]

    Computes N, mean, SD, p50, p90 for each of the 18 FEATURE_COLUMNS
    and writes a booktabs-style LaTeX tabular to tab_descriptive_stats.tex.

    Parameters
    ----------
    features_parquet : Path
        Path to the features parquet file.
    out_dir : Path
        Directory where tab_descriptive_stats.tex will be saved.
    """
    df = read_features_parquet(features_parquet)

    rows: list[str] = []
    for feat in FEATURE_COLUMNS:
        col = df[feat]
        valid = col.dropna()
        n = len(valid)
        mean = valid.mean()
        sd = valid.std()
        p50 = valid.quantile(0.5)
        p90 = valid.quantile(0.9)

        # Escape underscores for LaTeX
        feat_tex = feat.replace("_", r"\_")
        rows.append(
            f"{feat_tex} & {n} & {mean:.3f} & {sd:.3f} & {p50:.3f} & {p90:.3f} \\\\"
        )

    body = "\n".join(rows)
    latex = (
        "\\begin{tabular}{lrrrrr}\n"
        "\\toprule\n"
        "Feature & $N$ & Mean & SD & p50 & p90 \\\\\n"
        "\\midrule\n"
        f"{body}\n"
        "\\bottomrule\n"
        "\\end{tabular}\n"
    )

    out_path = out_dir / "tab_descriptive_stats.tex"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(latex, encoding="utf-8")


def gen_descriptive_stats_full_table(features_df: pd.DataFrame, out_dir: Path) -> None:
    """Generate extended descriptive statistics LaTeX table. [Task 10.3]

    Computes 9 statistics (N, mean, SD, min, p25, p50, p75, p90, max)
    for each of the 18 FEATURE_COLUMNS and writes a booktabs-style
    LaTeX tabular to tab_descriptive_stats_full.tex.

    Parameters
    ----------
    features_df : pd.DataFrame
        DataFrame containing the 18 feature columns.
    out_dir : Path
        Directory where tab_descriptive_stats_full.tex will be saved.

    Raises
    ------
    ValueError
        If features_df is empty or missing all expected columns.
    """
    if features_df.empty:
        raise ValueError("features_df is empty — cannot compute descriptive statistics")

    rows: list[str] = []
    for feat in FEATURE_COLUMNS:
        if feat not in features_df.columns:
            raise ValueError(f"Missing expected column: {feat}")
        col = features_df[feat]
        valid = col.dropna()
        n = len(valid)
        if n == 0:
            # All NaN — fill with dashes
            feat_tex = feat.replace("_", r"\_")
            rows.append(
                f"{feat_tex} & {n} & --- & --- & --- & --- & --- & --- & --- & --- \\\\"
            )
            continue
        mean = valid.mean()
        sd = valid.std()
        vmin = valid.min()
        p25 = valid.quantile(0.25)
        p50 = valid.quantile(0.5)
        p75 = valid.quantile(0.75)
        p90 = valid.quantile(0.9)
        vmax = valid.max()

        feat_tex = feat.replace("_", r"\_")
        rows.append(
            f"{feat_tex} & {n} & {mean:.3f} & {sd:.3f} & {vmin:.3f} "
            f"& {p25:.3f} & {p50:.3f} & {p75:.3f} & {p90:.3f} & {vmax:.3f} \\\\"
        )

    body = "\n".join(rows)
    latex = (
        "\\begin{tabular}{lrrrrrrrrr}\n"
        "\\toprule\n"
        "Feature & $N$ & Mean & SD & Min & p25 & p50 & p75 & p90 & Max \\\\\n"
        "\\midrule\n"
        f"{body}\n"
        "\\bottomrule\n"
        "\\end{tabular}\n"
    )

    out_path = out_dir / "tab_descriptive_stats_full.tex"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(latex, encoding="utf-8")


def gen_feature_distribution(features_df: pd.DataFrame, out_dir: Path) -> None:
    """Generate violin plot of 18 feature distributions grouped by category.

    Creates a multi-panel figure (one panel per category: PG/FILL/IX/RESP)
    showing the distribution of each feature as a violin plot.

    Parameters
    ----------
    features_df : pd.DataFrame
        DataFrame containing the 18 feature columns.
    out_dir : Path
        Directory where fig_feature_distribution.png will be saved.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # Group the 18 FEATURE_COLUMNS by category prefix (PG/FILL/IX/RESP)
    categories = ["PG", "FILL", "IX", "RESP"]
    cat_feats: dict[str, list[str]] = {c: [] for c in categories}
    cat_summaries: dict[str, list[str]] = {c: [] for c in categories}
    for name in FEATURE_COLUMNS:
        for cat in categories:
            if name.startswith(cat + "_"):
                cat_feats[cat].append(name)
                # Short label: strip category prefix for readability
                short = name[len(cat) + 1:]
                cat_summaries[cat].append(short)
                break

    n_cats = len(categories)
    fig, axes = plt.subplots(1, n_cats, figsize=(18, 5.5),
                             gridspec_kw={"width_ratios": [
                                 len(cat_feats[c]) for c in categories
                             ]})

    cat_colors = {
        "PG": "#2166ac",
        "FILL": "#4daf4a",
        "IX": "#ff7f00",
        "RESP": "#984ea3",
    }

    for idx, cat in enumerate(categories):
        ax = axes[idx]
        names = cat_feats[cat]
        labels = cat_summaries[cat]

        # Collect data for violin plot, dropping NaN per feature
        data_list = []
        valid_labels = []
        for name, label in zip(names, labels):
            if name in features_df.columns:
                vals = features_df[name].dropna().values
                if len(vals) > 0:
                    data_list.append(vals)
                    valid_labels.append(label)

        if not data_list:
            ax.set_title(f"{cat}", fontsize=12, fontweight="bold")
            ax.text(0.5, 0.5, "No data", ha="center", va="center",
                    transform=ax.transAxes, fontsize=10, color="grey")
            continue

        color = cat_colors.get(cat, "#333333")
        parts = ax.violinplot(data_list, positions=range(len(data_list)),
                              showmeans=True, showmedians=True,
                              showextrema=True)

        # Style violin bodies
        for pc in parts["bodies"]:
            pc.set_facecolor(color)
            pc.set_alpha(0.6)
            pc.set_edgecolor(color)
        # Style lines
        for key in ("cmeans", "cmedians", "cbars", "cmins", "cmaxes"):
            if key in parts:
                parts[key].set_color(color)
                parts[key].set_linewidth(1.2)

        ax.set_xticks(range(len(valid_labels)))
        ax.set_xticklabels(valid_labels, fontsize=8, rotation=45, ha="right")
        ax.set_title(f"{cat}", fontsize=12, fontweight="bold", color=color)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.tick_params(axis="y", labelsize=9)

    fig.suptitle("Distribution of 18 Interaction Features by Category",
                 fontsize=13, fontweight="bold", y=1.02)
    fig.tight_layout()
    out_path = out_dir / "fig_feature_distribution.png"
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def gen_corr_heatmap_block(features_df: pd.DataFrame, out_dir: Path) -> None:
    """Generate correlation heatmap with category block structure. [Task 10.4]

    Computes the Pearson correlation matrix for the 18 FEATURE_COLUMNS,
    orders them by category (PG → FILL → IX → RESP), draws a heatmap
    with category boundary lines, and saves both the PNG figure and a
    LaTeX tabular of the full correlation matrix.

    Parameters
    ----------
    features_df : pd.DataFrame
        DataFrame containing the 18 feature columns.
    out_dir : Path
        Directory where fig_corr_heatmap_block.png and tab_corr_matrix.tex
        will be saved.

    Raises
    ------
    ValueError
        If features_df is empty or missing all expected columns.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import TwoSlopeNorm

    if features_df.empty:
        raise ValueError("features_df is empty — cannot compute correlation matrix")

    # --- Order features by category: PG → FILL → IX → RESP ---
    category_order = ["PG", "FILL", "IX", "RESP"]
    ordered_cols: list[str] = []
    cat_sizes: list[int] = []
    for cat in category_order:
        prefix = cat + "_"
        cols = [c for c in FEATURE_COLUMNS if c.startswith(prefix)]
        ordered_cols.extend(cols)
        cat_sizes.append(len(cols))

    # Filter to available columns only
    available = [c for c in ordered_cols if c in features_df.columns]
    if not available:
        raise ValueError("No expected feature columns found in features_df")

    # Compute Pearson correlation (pairwise NaN handling)
    corr = features_df[available].corr(method="pearson")

    n = len(available)

    # --- Short labels for tick marks ---
    short_labels = []
    for name in available:
        for cat in category_order:
            if name.startswith(cat + "_"):
                short_labels.append(name[len(cat) + 1:])
                break
        else:
            short_labels.append(name)

    # --- Draw heatmap ---
    fig, ax = plt.subplots(figsize=(12, 10))

    norm = TwoSlopeNorm(vmin=-1, vcenter=0, vmax=1)
    im = ax.imshow(corr.values, cmap="RdBu_r", norm=norm, aspect="equal")

    # Annotate cells with correlation values (small font for readability)
    for i in range(n):
        for j in range(n):
            val = corr.values[i, j]
            # Use white text on dark backgrounds
            text_color = "white" if abs(val) > 0.6 else "black"
            ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                    fontsize=7, color=text_color)

    # --- Category boundary lines ---
    cumulative = 0
    for k, size in enumerate(cat_sizes):
        cumulative += size
        if k < len(cat_sizes) - 1 and cumulative <= n:
            # Draw thick black lines at category boundaries
            ax.axhline(y=cumulative - 0.5, color="black", linewidth=2.0)
            ax.axvline(x=cumulative - 0.5, color="black", linewidth=2.0)

    # --- Category labels on top ---
    cumulative = 0
    for cat, size in zip(category_order, cat_sizes):
        if size > 0:
            mid = cumulative + size / 2 - 0.5
            ax.text(mid, -1.5, cat, ha="center", va="center",
                    fontsize=12, fontweight="bold",
                    color={"PG": "#2166ac", "FILL": "#4daf4a",
                           "IX": "#ff7f00", "RESP": "#984ea3"}.get(cat, "black"))
            cumulative += size

    # --- Tick labels ---
    ax.set_xticks(range(n))
    ax.set_xticklabels(short_labels, fontsize=7, rotation=55, ha="right")
    ax.set_yticks(range(n))
    ax.set_yticklabels(short_labels, fontsize=7)

    ax.set_title("Pearson Correlation Matrix (Block Structure: PG → FILL → IX → RESP)",
                 fontsize=12, fontweight="bold", pad=28)

    # Colorbar
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, shrink=0.85)
    cbar.set_label("Pearson r", fontsize=10)
    cbar.set_ticks([-1.0, -0.5, 0.0, 0.5, 1.0])

    fig.tight_layout()
    out_path = out_dir / "fig_corr_heatmap_block.png"
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)

    # --- Generate LaTeX correlation matrix table ---
    _gen_tab_corr_matrix(corr, available, out_dir)


def _gen_tab_corr_matrix(
    corr: pd.DataFrame, ordered_cols: list[str], out_dir: Path
) -> None:
    """Write the full 18×18 correlation matrix as a LaTeX tabular.

    Uses small font and landscape-friendly formatting since 18×18 is large.
    Correlations are rounded to 2 decimal places.

    Parameters
    ----------
    corr : pd.DataFrame
        Correlation matrix (features × features).
    ordered_cols : list[str]
        Column names in display order.
    out_dir : Path
        Output directory for tab_corr_matrix.tex.
    """
    n = len(ordered_cols)

    # Short column headers (numbered for compactness)
    short_names = []
    for name in ordered_cols:
        for cat in ["PG", "FILL", "IX", "RESP"]:
            if name.startswith(cat + "_"):
                short_names.append(name[len(cat) + 1:])
                break
        else:
            short_names.append(name)

    # Escape underscores for LaTeX
    tex_short = [s.replace("_", r"\_") for s in short_names]
    tex_full = [c.replace("_", r"\_") for c in ordered_cols]

    # Build column spec: l + n right-aligned columns
    col_spec = "l" + "r" * n

    # Header row: numbered columns for compactness
    header_nums = " & ".join(str(i + 1) for i in range(n))

    # Build rows
    rows: list[str] = []
    for i in range(n):
        vals = []
        for j in range(n):
            v = corr.values[i, j]
            if i == j:
                vals.append("---")
            elif np.isnan(v):
                vals.append("NaN")
            else:
                vals.append(f"{v:.2f}")
        row_label = f"({i + 1}) {tex_full[i]}"
        rows.append(f"{row_label} & {' & '.join(vals)} \\\\")

    body = "\n".join(rows)

    # Legend: numbered column mapping
    legend_items = [f"({i + 1}) {tex_full[i]}" for i in range(n)]
    legend = ", ".join(legend_items)

    latex = (
        "{\\tiny\n"
        f"\\begin{{tabular}}{{{col_spec}}}\n"
        "\\toprule\n"
        f" & {header_nums} \\\\\n"
        "\\midrule\n"
        f"{body}\n"
        "\\bottomrule\n"
        "\\end{tabular}\n"
        "}\n"
        "\n"
        "\\vspace{2mm}\n"
        "{\\scriptsize\n"
        f"\\textit{{Column key}}: {legend}\n"
        "}\n"
    )

    out_path = out_dir / "tab_corr_matrix.tex"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(latex, encoding="utf-8")


def gen_metadata_gender(
    features_df: pd.DataFrame, metadata_df: pd.DataFrame, out_dir: Path
) -> None:
    """Generate gender × feature boxplots with Mann-Whitney U tests. [Task 10.5]

    For each of the 18 features, draws side-by-side boxplots for M vs F
    and annotates each subplot with the Mann-Whitney U statistic and p-value.

    Parameters
    ----------
    features_df : pd.DataFrame
        DataFrame containing the 18 feature columns and ``speaker_id``.
    metadata_df : pd.DataFrame
        DataFrame containing at least ``speaker_id`` and ``gender`` columns.
    out_dir : Path
        Directory where fig_metadata_gender.png will be saved.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from scipy.stats import mannwhitneyu

    if "gender" not in metadata_df.columns:
        print(
            "WARNING: metadata に 'gender' カラムがありません — "
            "fig_metadata_gender.png の生成をスキップします",
            file=sys.stderr,
        )
        return

    # Merge on (conversation_id, speaker_id) — speaker_id alone is not unique
    merge_keys = ["conversation_id", "speaker_id"] if "conversation_id" in metadata_df.columns else ["speaker_id"]
    merged = features_df.merge(metadata_df[merge_keys + ["gender"]], on=merge_keys, how="left")
    merged = merged.dropna(subset=["gender"])

    males = merged[merged["gender"] == "M"]
    females = merged[merged["gender"] == "F"]

    if len(males) == 0 or len(females) == 0:
        print(
            "WARNING: 性別が1群のみ — fig_metadata_gender.png の生成をスキップします",
            file=sys.stderr,
        )
        return

    n_features = len(FEATURE_COLUMNS)
    n_cols = 3
    n_rows = (n_features + n_cols - 1) // n_cols  # ceil division → 6

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(14, n_rows * 3.2))
    axes_flat = axes.flatten()

    for idx, feat in enumerate(FEATURE_COLUMNS):
        ax = axes_flat[idx]
        m_vals = males[feat].dropna().values
        f_vals = females[feat].dropna().values

        # Boxplot
        bp = ax.boxplot(
            [m_vals, f_vals],
            tick_labels=["M", "F"],
            patch_artist=True,
            widths=0.5,
        )
        bp["boxes"][0].set_facecolor("#4393c3")
        bp["boxes"][1].set_facecolor("#d6604d")
        bp["boxes"][0].set_alpha(0.7)
        bp["boxes"][1].set_alpha(0.7)

        # Mann-Whitney U test
        if len(m_vals) >= 1 and len(f_vals) >= 1:
            try:
                u_stat, p_val = mannwhitneyu(m_vals, f_vals, alternative="two-sided")
                sig_marker = " *" if p_val < 0.05 else ""
                ax.set_title(
                    f"{feat}\nU={u_stat:.0f}, p={p_val:.4f}{sig_marker}",
                    fontsize=9,
                    fontweight="bold" if p_val < 0.05 else "normal",
                )
            except ValueError:
                ax.set_title(f"{feat}\n(test N/A)", fontsize=9)
        else:
            ax.set_title(f"{feat}\n(insufficient data)", fontsize=9)

        ax.tick_params(axis="both", labelsize=8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    # Hide unused subplots
    for idx in range(n_features, len(axes_flat)):
        axes_flat[idx].set_visible(False)

    fig.suptitle(
        f"Gender × Feature Comparison (M: n={len(males)}, F: n={len(females)})",
        fontsize=13, fontweight="bold", y=1.01,
    )
    fig.tight_layout()
    out_path = out_dir / "fig_metadata_gender.png"
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def gen_metadata_age(
    features_df: pd.DataFrame, metadata_df: pd.DataFrame, out_dir: Path
) -> None:
    """Generate age × feature scatter plots with correlation annotations. [Task 10.5]

    For each of the 18 features, draws a scatter plot of age vs feature value,
    overlays a regression line, and annotates with Pearson r and Spearman rho.

    Parameters
    ----------
    features_df : pd.DataFrame
        DataFrame containing the 18 feature columns and ``speaker_id``.
    metadata_df : pd.DataFrame
        DataFrame containing at least ``speaker_id`` and ``age`` columns.
    out_dir : Path
        Directory where fig_metadata_age.png will be saved.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from scipy.stats import pearsonr, spearmanr

    if "age" not in metadata_df.columns:
        print(
            "WARNING: metadata に 'age' カラムがありません — "
            "fig_metadata_age.png の生成をスキップします",
            file=sys.stderr,
        )
        return

    # Merge on (conversation_id, speaker_id) — speaker_id alone is not unique
    merge_keys = ["conversation_id", "speaker_id"] if "conversation_id" in metadata_df.columns else ["speaker_id"]
    merged = features_df.merge(metadata_df[merge_keys + ["age"]], on=merge_keys, how="left")
    merged["age"] = pd.to_numeric(merged["age"], errors="coerce")
    merged = merged.dropna(subset=["age"])

    if len(merged) == 0:
        print(
            "WARNING: 有効な年齢データがありません — "
            "fig_metadata_age.png の生成をスキップします",
            file=sys.stderr,
        )
        return

    n_features = len(FEATURE_COLUMNS)
    n_cols = 3
    n_rows = (n_features + n_cols - 1) // n_cols

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(14, n_rows * 3.2))
    axes_flat = axes.flatten()

    for idx, feat in enumerate(FEATURE_COLUMNS):
        ax = axes_flat[idx]
        valid = merged[["age", feat]].dropna()
        age_vals = valid["age"].values
        feat_vals = valid[feat].values

        ax.scatter(age_vals, feat_vals, alpha=0.5, s=18, color="#2166ac", edgecolors="white", linewidths=0.3)

        annotation_lines = [feat]

        if len(valid) >= 3:
            # Regression line
            try:
                z = np.polyfit(age_vals, feat_vals, 1)
                p_line = np.poly1d(z)
                x_range = np.linspace(age_vals.min(), age_vals.max(), 50)
                ax.plot(x_range, p_line(x_range), color="#d6604d", linewidth=1.2, linestyle="--")
            except (np.linalg.LinAlgError, ValueError):
                pass

            # Pearson
            try:
                r_p, p_p = pearsonr(age_vals, feat_vals)
                sig_p = "*" if p_p < 0.05 else ""
                annotation_lines.append(f"r={r_p:.3f}, p={p_p:.4f}{sig_p}")
            except ValueError:
                annotation_lines.append("Pearson: N/A")

            # Spearman
            try:
                rho_s, p_s = spearmanr(age_vals, feat_vals)
                sig_s = "*" if p_s < 0.05 else ""
                annotation_lines.append(f"ρ={rho_s:.3f}, p={p_s:.4f}{sig_s}")
            except ValueError:
                annotation_lines.append("Spearman: N/A")
        else:
            annotation_lines.append("(n < 3)")

        ax.set_title("\n".join(annotation_lines), fontsize=9, fontweight="normal")
        ax.set_xlabel("Age", fontsize=9)
        ax.tick_params(axis="both", labelsize=8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    # Hide unused subplots
    for idx in range(n_features, len(axes_flat)):
        axes_flat[idx].set_visible(False)

    fig.suptitle(
        f"Age × Feature Correlation (n={len(merged)})",
        fontsize=13, fontweight="bold", y=1.01,
    )
    fig.tight_layout()
    out_path = out_dir / "fig_metadata_age.png"
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def gen_tab_metadata_tests(
    features_df: pd.DataFrame, metadata_df: pd.DataFrame, out_dir: Path
) -> None:
    """Generate summary LaTeX table of metadata association tests. [Task 10.5]

    Produces a table with one row per feature and columns for:
    - Gender: Mann-Whitney U statistic and p-value
    - Age: Pearson r and p, Spearman rho and p

    Parameters
    ----------
    features_df : pd.DataFrame
        DataFrame containing the 18 feature columns and ``speaker_id``.
    metadata_df : pd.DataFrame
        DataFrame containing at least ``speaker_id`` and optionally
        ``gender`` and ``age`` columns.
    out_dir : Path
        Directory where tab_metadata_tests.tex will be saved.
    """
    from scipy.stats import mannwhitneyu, pearsonr, spearmanr

    has_gender = "gender" in metadata_df.columns
    has_age = "age" in metadata_df.columns

    # Merge on (conversation_id, speaker_id) — speaker_id alone is not unique
    merge_keys = ["conversation_id", "speaker_id"] if "conversation_id" in metadata_df.columns else ["speaker_id"]
    merge_cols = list(merge_keys)
    if has_gender:
        merge_cols.append("gender")
    if has_age:
        merge_cols.append("age")
    merged = features_df.merge(metadata_df[merge_cols], on=merge_keys, how="left")

    if has_age:
        merged["age"] = pd.to_numeric(merged["age"], errors="coerce")

    if has_gender:
        males = merged[merged["gender"] == "M"]
        females = merged[merged["gender"] == "F"]
        gender_ok = len(males) > 0 and len(females) > 0
    else:
        gender_ok = False

    rows: list[str] = []
    for feat in FEATURE_COLUMNS:
        feat_tex = feat.replace("_", r"\_")

        # --- Gender: Mann-Whitney U ---
        if gender_ok:
            m_vals = males[feat].dropna().values
            f_vals = females[feat].dropna().values
            if len(m_vals) >= 1 and len(f_vals) >= 1:
                try:
                    u_stat, g_p = mannwhitneyu(m_vals, f_vals, alternative="two-sided")
                    u_str = f"{u_stat:.0f}"
                    gp_str = f"{g_p:.4f}"
                    if g_p < 0.05:
                        u_str = f"\\textbf{{{u_str}}}"
                        gp_str = f"\\textbf{{{gp_str}*}}"
                except ValueError:
                    u_str, gp_str = "---", "---"
            else:
                u_str, gp_str = "---", "---"
        else:
            u_str, gp_str = "---", "---"

        # --- Age: Pearson & Spearman ---
        if has_age:
            valid = merged[["age", feat]].dropna()
            age_vals = valid["age"].values
            feat_vals = valid[feat].values
            if len(valid) >= 3:
                try:
                    r_p, p_p = pearsonr(age_vals, feat_vals)
                    rp_str = f"{r_p:.3f}"
                    pp_str = f"{p_p:.4f}"
                    if p_p < 0.05:
                        rp_str = f"\\textbf{{{rp_str}}}"
                        pp_str = f"\\textbf{{{pp_str}*}}"
                except ValueError:
                    rp_str, pp_str = "---", "---"
                try:
                    rho_s, p_s = spearmanr(age_vals, feat_vals)
                    rs_str = f"{rho_s:.3f}"
                    ps_str = f"{p_s:.4f}"
                    if p_s < 0.05:
                        rs_str = f"\\textbf{{{rs_str}}}"
                        ps_str = f"\\textbf{{{ps_str}*}}"
                except ValueError:
                    rs_str, ps_str = "---", "---"
            else:
                rp_str, pp_str, rs_str, ps_str = "---", "---", "---", "---"
        else:
            rp_str, pp_str, rs_str, ps_str = "---", "---", "---", "---"

        rows.append(
            f"{feat_tex} & {u_str} & {gp_str} & {rp_str} & {pp_str} & {rs_str} & {ps_str} \\\\"
        )

    body = "\n".join(rows)
    latex = (
        "{\\small\n"
        "\\begin{tabular}{lrrrrrr}\n"
        "\\toprule\n"
        "Feature & $U$ & $p_{\\text{gender}}$ "
        "& $r_{\\text{Pearson}}$ & $p_{\\text{Pearson}}$ "
        "& $\\rho_{\\text{Spearman}}$ & $p_{\\text{Spearman}}$ \\\\\n"
        "\\midrule\n"
        f"{body}\n"
        "\\bottomrule\n"
        "\\end{tabular}\n"
        "}\n"
    )

    out_path = out_dir / "tab_metadata_tests.tex"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(latex, encoding="utf-8")


def gen_tab_permutation_all(results_dir: Path, out_dir: Path) -> None:
    """Generate full permutation results LaTeX table. [Task 1.8]

    Rows: 5 traits (C, A, E, N, O).
    Columns: 4 teachers (Sonnet4, Qwen3-235B, GPT-OSS-120B, DeepSeek-V3).
    Each cell: r_obs (p-value), bold if p < 0.05.
    Missing permutation.log → "---".

    Parameters
    ----------
    results_dir : Path
        Root directory containing permutation result sub-directories.
    out_dir : Path
        Directory where tab_permutation_all.tex will be saved.
    """
    header_teachers = " & ".join(TEACHER_DISPLAY[t] for t in TEACHERS)
    rows: list[str] = []

    for trait in TRAITS:
        cells: list[str] = []
        for teacher in TEACHERS:
            log_path = permutation_log_path(results_dir, trait, teacher)
            if not log_path.exists():
                cells.append("---")
                continue
            try:
                res = parse_permutation_log(log_path)
            except (ValueError, FileNotFoundError):
                cells.append("---")
                continue
            cell_text = f"{res.r_obs:.3f} ({res.p_value:.4f})"
            if res.p_value < 0.05:
                cell_text = f"\\textbf{{{cell_text}}}"
            cells.append(cell_text)
        rows.append(f"{trait} & {' & '.join(cells)} \\\\")

    body = "\n".join(rows)
    latex = (
        "\\begin{tabular}{lcccc}\n"
        "\\toprule\n"
        f"Trait & {header_teachers} \\\\\n"
        "\\midrule\n"
        f"{body}\n"
        "\\bottomrule\n"
        "\\end{tabular}\n"
    )

    out_path = out_dir / "tab_permutation_all.tex"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(latex, encoding="utf-8")


def gen_tab_ensemble_permutation(results_dir: Path, out_dir: Path) -> None:
    """Generate ensemble permutation results LaTeX table (tab_ensemble_permutation.tex).

    Reads ensemble_summary.tsv and produces a booktabs-style LaTeX table
    with rows for each trait (O, C, E, A, N) and columns: Trait, r_obs, p-value.
    Significant results (p < 0.05) are bolded.

    Parameters
    ----------
    results_dir : Path
        Directory containing ``ensemble_summary.tsv``
        (columns: trait, r_obs, p_value).
    out_dir : Path
        Directory where tab_ensemble_permutation.tex will be saved.

    Raises
    ------
    FileNotFoundError
        If ensemble_summary.tsv does not exist.
    """
    summary_path = results_dir / "ensemble_summary.tsv"
    if not summary_path.exists():
        raise FileNotFoundError(
            f"ensemble_summary.tsv not found: {summary_path}\n"
            f"Expected columns: trait, r_obs, p_value"
        )

    df = pd.read_csv(summary_path, sep="\t")

    trait_order = ["O", "C", "E", "A", "N"]
    df = df.set_index("trait").loc[trait_order].reset_index()

    rows: list[str] = []
    for _, row in df.iterrows():
        trait = row["trait"]
        r_obs = row["r_obs"]
        p_val = row["p_value"]
        r_str = f"{r_obs:.3f}"
        p_str = f"{p_val:.4f}"
        if p_val < 0.05:
            r_str = f"\\textbf{{{r_str}}}"
            p_str = f"\\textbf{{{p_str}}}"
        rows.append(f"{trait} & {r_str} & {p_str} \\\\")

    body = "\n".join(rows)
    latex = (
        "\\begin{tabular}{lcc}\n"
        "\\toprule\n"
        "Trait & $r_{obs}$ & $p$-value \\\\\n"
        "\\midrule\n"
        f"{body}\n"
        "\\bottomrule\n"
        "\\end{tabular}\n"
    )

    out_path = out_dir / "tab_ensemble_permutation.tex"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(latex, encoding="utf-8")


def gen_tab_baseline_vs_extended(results_dir: Path, out_dir: Path) -> None:
    """Generate baseline vs extended comparison LaTeX table (tab_baseline_vs_extended.tex).

    Reads all ``baseline_vs_extended_*.tsv`` files from *results_dir* and
    produces a booktabs-style LaTeX table with rows for each trait (O, C, E, A, N)
    and columns: Trait, r_baseline, r_extended, Δr.
    If multiple teachers exist for the same trait, values are averaged across teachers.
    Significant improvements (Δr > 0) are bolded.

    Parameters
    ----------
    results_dir : Path
        Directory containing ``baseline_vs_extended_*.tsv`` files
        (columns: trait, teacher, r_baseline, p_baseline, r_extended,
        p_extended, delta_r).
    out_dir : Path
        Directory where tab_baseline_vs_extended.tex will be saved.

    Raises
    ------
    FileNotFoundError
        If no baseline_vs_extended_*.tsv files are found.
    """
    tsv_files = sorted(results_dir.glob("baseline_vs_extended_*.tsv"))
    if not tsv_files:
        raise FileNotFoundError(
            f"No baseline_vs_extended_*.tsv files found in: {results_dir}\n"
            f"Expected columns: trait, teacher, r_baseline, p_baseline, "
            f"r_extended, p_extended, delta_r"
        )

    frames = [pd.read_csv(f, sep="\t") for f in tsv_files]
    df = pd.concat(frames, ignore_index=True)

    # Average across teachers per trait
    agg = df.groupby("trait")[["r_baseline", "r_extended", "delta_r"]].mean()

    trait_order = ["O", "C", "E", "A", "N"]
    rows: list[str] = []
    for trait in trait_order:
        if trait not in agg.index:
            rows.append(f"{trait} & --- & --- & --- \\\\")
            continue
        r_base = agg.loc[trait, "r_baseline"]
        r_ext = agg.loc[trait, "r_extended"]
        dr = agg.loc[trait, "delta_r"]
        r_base_str = f"{r_base:.3f}"
        r_ext_str = f"{r_ext:.3f}"
        sign = "+" if dr >= 0 else ""
        dr_str = f"{sign}{dr:.3f}"
        if dr > 0:
            r_ext_str = f"\\textbf{{{r_ext_str}}}"
            dr_str = f"\\textbf{{{dr_str}}}"
        rows.append(f"{trait} & {r_base_str} & {r_ext_str} & {dr_str} \\\\")

    body = "\n".join(rows)
    latex = (
        "\\begin{tabular}{lccc}\n"
        "\\toprule\n"
        "Trait & $r_{baseline}$ & $r_{extended}$ & $\\Delta r$ \\\\\n"
        "\\midrule\n"
        f"{body}\n"
        "\\bottomrule\n"
        "\\end{tabular}\n"
    )

    out_path = out_dir / "tab_baseline_vs_extended.tex"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(latex, encoding="utf-8")


def gen_tab_feature_definitions(out_dir: Path) -> None:
    """Generate feature definitions LaTeX table with Classification column.

    Outputs a booktabs-style LaTeX longtable with 18 rows (explanatory
    features only), each containing: Name, Cat., Class., Summary, Algorithm.

    The feature data is sourced from ``feature_definitions.py`` via
    ``get_explanatory_features()``, which provides the ``classification``
    field ("Classical" or "Novel") for each feature.

    Parameters
    ----------
    out_dir : Path
        Directory where tab_feature_definitions.tex will be saved.
    """
    explanatory = get_explanatory_features()

    def _escape_latex(text: str) -> str:
        """Escape special LaTeX characters in free-text fields."""
        text = text.replace("_", r"\_")
        text = text.replace("->", r"$\rightarrow$")
        text = text.replace(">=", r"$\geq$")
        return text

    rows: list[str] = []
    for feat in explanatory:
        name_tex = feat.name.replace("_", r"\_")
        algo_tex = _escape_latex(feat.algorithm)
        summary_tex = _escape_latex(feat.summary)
        rows.append(
            f"{name_tex} & {feat.category} & {feat.classification} "
            f"& {summary_tex} & {algo_tex} \\\\"
        )

    body = "\n".join(rows)
    latex = (
        "{\\small\n"
        "\\begin{longtable}{lllp{3.0cm}p{5.8cm}}\n"
        "\\toprule\n"
        "Name & Cat. & Class. & Summary & Algorithm \\\\\n"
        "\\midrule\n"
        "\\endhead\n"
        f"{body}\n"
        "\\bottomrule\n"
        "\\end{longtable}\n"
        "}\n"
    )

    out_path = out_dir / "tab_feature_definitions.tex"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(latex, encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> None:
    """Entry point: parse CLI args, validate inputs, invoke generators."""
    parser = build_parser()
    args = parser.parse_args(argv)

    results_dir = Path(args.results_dir)
    bootstrap_dir = Path(args.bootstrap_dir)
    features_parquet = Path(args.features_parquet)
    out_dir = Path(args.out_dir)

    # --- Load metadata (optional — warn & skip if absent) ---
    metadata_df: pd.DataFrame | None = None
    if args.metadata_tsv is not None:
        metadata_df = load_metadata(args.metadata_tsv)
    else:
        print(
            "INFO: --metadata_tsv 未指定 — メタデータ関連図の生成をスキップします",
            file=sys.stderr,
        )

    # --- Validate input paths ---
    errors: list[str] = []

    if not results_dir.is_dir():
        errors.append(
            f"Results directory not found: {results_dir}\n"
            f"  Expected: directory containing cejc_home2_hq1_{{trait}}only_{{teacher}}_controls_excluded/permutation.log"
        )
    if not bootstrap_dir.is_dir():
        errors.append(
            f"Bootstrap directory not found: {bootstrap_dir}\n"
            f"  Expected: directory containing cejc_home2_hq1_{{trait}}only_{{teacher}}_controls_excluded/bootstrap_summary.tsv"
        )
    if not features_parquet.exists():
        errors.append(
            f"Features parquet not found: {features_parquet}\n"
            f"  Expected columns: {', '.join(FEATURE_COLUMNS)}"
        )

    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        sys.exit(1)

    # --- Create output directory ---
    out_dir.mkdir(parents=True, exist_ok=True)

    # --- Generate figures and tables ---
    # Each generator catches its own errors and prints warnings to stderr
    # so that failure in one does not block the others.
    # --- Load features DataFrame for new figure generators ---
    features_df = read_features_parquet(features_parquet)

    generators = [
        ("fig_permutation_C_bar.png", gen_fig_permutation_C_bar, [results_dir, out_dir]),
        ("fig_bootstrap_C_radar.png", gen_fig_bootstrap_C_radar, [bootstrap_dir, out_dir]),
        ("fig_teacher_heatmap.png", gen_fig_teacher_heatmap, [out_dir]),
        ("tab_descriptive_stats.tex", gen_tab_descriptive_stats, [features_parquet, out_dir]),
        ("tab_permutation_all.tex", gen_tab_permutation_all, [results_dir, out_dir]),
        ("tab_feature_definitions.tex", gen_tab_feature_definitions, [out_dir]),
        ("fig_feature_distribution.png", gen_feature_distribution, [features_df, out_dir]),
        ("tab_descriptive_stats_full.tex", gen_descriptive_stats_full_table, [features_df, out_dir]),
        ("fig_corr_heatmap_block.png + tab_corr_matrix.tex", gen_corr_heatmap_block, [features_df, out_dir]),
        # --- New ensemble / baseline-vs-extended figures and tables ---
        ("fig_ensemble_permutation.png", gen_fig_ensemble_permutation, [results_dir, out_dir]),
        ("fig_baseline_vs_extended.png", gen_fig_baseline_vs_extended, [results_dir, out_dir]),
        ("tab_ensemble_permutation.tex", gen_tab_ensemble_permutation, [results_dir, out_dir]),
        ("tab_baseline_vs_extended.tex", gen_tab_baseline_vs_extended, [results_dir, out_dir]),
    ]

    # --- Metadata-related generators (only when metadata is available) ---
    if metadata_df is not None:
        generators.append(
            ("fig_metadata_gender.png", gen_metadata_gender, [features_df, metadata_df, out_dir])
        )
        generators.append(
            ("fig_metadata_age.png", gen_metadata_age, [features_df, metadata_df, out_dir])
        )
        generators.append(
            ("tab_metadata_tests.tex", gen_tab_metadata_tests, [features_df, metadata_df, out_dir])
        )

    for name, func, func_args in generators:
        try:
            func(*func_args)
            print(f"  OK: {name}")
        except NotImplementedError:
            print(f"  SKIP (not yet implemented): {name}")
        except (ValueError, KeyError) as exc:
            print(f"  WARN: {name} — {exc}", file=sys.stderr)
        except FileNotFoundError as exc:
            print(f"  ERROR: {name} — {exc}", file=sys.stderr)

    print(f"\nDone. Output directory: {out_dir}")


if __name__ == "__main__":
    main()
