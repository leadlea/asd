#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_paper_figures.py

Generate paper-ready figures from "LLM labeling v0" aggregated rows.
Input: JSONL (one JSON object per line) OR JSON array file.

Expected fields per row (flexible):
- dataset, speaker_id, atypicality_v0
- CL_pca_x, CL_pca_y, CL_fillpg_cluster
- PG_*, FILL_*, IX_* metrics as top-level keys (recommended)
- labels: { labels: [ {label, confidence, why, used_features, used_examples}, ... ],
           summary, needs_more_context, missing }

Usage:
  python scripts/paper_figs/make_paper_figures.py --in rows.jsonl --out paper_figs
  python scripts/paper_figs/make_paper_figures.py --in rows.jsonl --out paper_figs --group primary_label
  python scripts/paper_figures.py --in rows.jsonl --out paper_figs --case-speaker K004_022:IC02
"""

import argparse
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

FEATURE_TOKEN_RE = re.compile(r"\b[A-Z]{2,}_[A-Za-z0-9_]+\b")

DEFAULT_METRICS = [
    "PG_pause_p50",
    "PG_pause_mean",
    "PG_resp_gap_p50",
    "PG_speech_ratio",
    "FILL_rate_per_100chars",
    "FILL_z_log_rate_per_100chars",
    "IX_oirmarker_rate",
    "IX_yesno_rate",
    "IX_lex_overlap_mean",
    "IX_topic_drift_mean",
]


def read_rows(path: Path):
    txt = path.read_text(encoding="utf-8")
    txt_strip = txt.lstrip()
    if txt_strip.startswith("["):
        arr = json.loads(txt)
        if not isinstance(arr, list):
            raise ValueError("JSON array file must contain a list.")
        return arr

    # JSONL
    rows = []
    for line in txt.splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def primary_label_from_labels(labels_obj):
    lab_list = (labels_obj or {}).get("labels", [])
    if not lab_list:
        return None, None
    best = max(lab_list, key=lambda x: float(x.get("confidence", 0.0) or 0.0))
    return best.get("label"), float(best.get("confidence", 0.0) or 0.0)


def extract_metrics(d):
    out = {}
    for k, v in d.items():
        if k.startswith(("PG_", "FILL_", "IX_", "CL_")):
            out[k] = v
    return out


def compute_mismatch_rate(labels_obj):
    """
    Detect simple inconsistency: features mentioned in "why" but missing from used_features.
    Returns mismatch_rate in [0,1] or np.nan if not applicable.
    """
    lab_list = (labels_obj or {}).get("labels", [])
    if not lab_list:
        return np.nan

    mismatches = []
    for ent in lab_list:
        why = ent.get("why", "") or ""
        mentioned = set(FEATURE_TOKEN_RE.findall(why))
        used = set(ent.get("used_features", []) or [])
        if not mentioned:
            continue
        missing = mentioned - used
        mismatches.append(len(missing) / max(1, len(mentioned)))

    if not mismatches:
        return np.nan
    return float(np.mean(mismatches))


def flatten_rows(rows):
    flat = []
    for r in rows:
        labels_obj = r.get("labels", None)
        prim, prim_conf = primary_label_from_labels(labels_obj)

        used_ex_cnt = 0
        for ent in (labels_obj or {}).get("labels", []) or []:
            used_ex_cnt += len(ent.get("used_examples", []) or [])

        row = {
            "dataset": r.get("dataset"),
            "speaker_id": r.get("speaker_id"),
            "atypicality_v0": r.get("atypicality_v0"),
            "primary_label": prim,
            "primary_conf": prim_conf,
            "needs_more_context": bool((labels_obj or {}).get("needs_more_context", False)),
            "missing_count": len((labels_obj or {}).get("missing", []) or []),
            "used_examples_count": used_ex_cnt,
            "why_usedfeat_mismatch_rate": compute_mismatch_rate(labels_obj),
        }
        row.update(extract_metrics(r))
        flat.append(row)

    return pd.DataFrame(flat)


def ensure_numeric(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def fig_pca(df, outdir: Path):
    req = {"CL_pca_x", "CL_pca_y", "CL_fillpg_cluster"}
    if not req.issubset(df.columns):
        return None

    plt.figure()
    for cl, sub in df.dropna(subset=["CL_pca_x", "CL_pca_y", "CL_fillpg_cluster"]).groupby("CL_fillpg_cluster"):
        plt.scatter(sub["CL_pca_x"], sub["CL_pca_y"], label=f"c{int(cl)}", s=18, alpha=0.9)

    plt.xlabel("PCA x")
    plt.ylabel("PCA y")
    plt.title("Cluster map (PCA)")
    plt.legend(title="cluster", loc="best", frameon=True)

    path = outdir / "fig3_pca_cluster.png"
    plt.tight_layout()
    plt.savefig(path, dpi=200)
    plt.close()
    return path


def cohen_d(x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    x = x[~np.isnan(x)]
    y = y[~np.isnan(y)]
    if len(x) < 2 or len(y) < 2:
        return np.nan

    nx, ny = len(x), len(y)
    vx, vy = np.var(x, ddof=1), np.var(y, ddof=1)
    sp = np.sqrt(((nx - 1) * vx + (ny - 1) * vy) / max(1, (nx + ny - 2)))
    if sp == 0:
        return np.nan
    return (np.mean(x) - np.mean(y)) / sp


def bootstrap_ci(func, x, y, n=2000, seed=0):
    rng = np.random.default_rng(seed)
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    x = x[~np.isnan(x)]
    y = y[~np.isnan(y)]
    if len(x) < 2 or len(y) < 2:
        return (np.nan, np.nan)

    stats = []
    for _ in range(n):
        xb = rng.choice(x, size=len(x), replace=True)
        yb = rng.choice(y, size=len(y), replace=True)
        stats.append(func(xb, yb))

    stats = np.asarray(stats, dtype=float)
    lo = np.nanpercentile(stats, 2.5)
    hi = np.nanpercentile(stats, 97.5)
    return (float(lo), float(hi))


def fig_effect_forest(df, outdir, group_var="dataset", metrics=None, title=None, min_n_per_group=10, n_boot=1000, seed=0):
    """
    Compute Cohen's d per metric with bootstrap CI.
    IMPORTANT: dropna is done PER-METRIC (not across all metrics), so missing metrics in one group won't wipe the group.
    """
    if metrics is None:
        metrics = list(DEFAULT_METRICS)

    if group_var not in df.columns:
        print(f"[WARN] effect_forest: group_var not found: {group_var}")
        return None

    groups = [g for g in df[group_var].dropna().unique().tolist()]
    if len(groups) != 2:
        print(f"[WARN] effect_forest: need exactly 2 groups, got {groups}")
        return None
    g0, g1 = groups[0], groups[1]

    rng = np.random.default_rng(seed)

    def cohen_d_local(x, y):
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        nx, ny = len(x), len(y)
        if nx < 2 or ny < 2:
            return np.nan
        vx = np.var(x, ddof=1)
        vy = np.var(y, ddof=1)
        pooled = ((nx - 1) * vx + (ny - 1) * vy) / (nx + ny - 2)
        if pooled <= 0 or not np.isfinite(pooled):
            return np.nan
        return (np.mean(x) - np.mean(y)) / np.sqrt(pooled)

    def boot_ci(x, y):
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        nx, ny = len(x), len(y)
        if nx < 2 or ny < 2:
            return (np.nan, np.nan)
        ds = []
        for _ in range(int(n_boot)):
            xb = x[rng.integers(0, nx, nx)]
            yb = y[rng.integers(0, ny, ny)]
            ds.append(cohen_d_local(xb, yb))
        ds = np.asarray(ds, dtype=float)
        ds = ds[np.isfinite(ds)]
        if len(ds) == 0:
            return (np.nan, np.nan)
        return (np.percentile(ds, 2.5), np.percentile(ds, 97.5))

    # filter metrics that are missing in any group (or too small N)
    # drop metrics not present in df
    metrics = [m for m in metrics if m in df.columns]
    min_n_per_group = int(min_n_per_group or 2)
    groups = sorted(list(df[group_var].dropna().unique()))
    metrics_keep = []
    metrics_drop = []
    for m in metrics:
        # skip metrics absent in this flattened table
        if m not in df.columns:
            continue
        counts = [(g, int(df.loc[df[group_var] == g, m].notna().sum())) for g in groups]
        if all(c >= min_n_per_group for _, c in counts):
            metrics_keep.append(m)
        else:
            metrics_drop.append((m, counts))
    if metrics_drop:
        for m, counts in metrics_drop:
            print(f"DROP {m} {counts}")
    metrics = metrics_keep
    if not metrics:
        print("WARN: no metrics left after filtering; skipping effect-forest.")
        return None

    rows = []
    dropped = []

    for m in metrics:
        if m not in df.columns:
            dropped.append((m, "missing_col", 0, 0))
            continue
        x = df.loc[df[group_var] == g0, m].dropna().astype(float).values
        y = df.loc[df[group_var] == g1, m].dropna().astype(float).values
        n0, n1 = len(x), len(y)

        if n0 < min_n_per_group or n1 < min_n_per_group:
            dropped.append((m, f"n<{min_n_per_group}", n0, n1))
            continue

        d = cohen_d_local(x, y)
        if not np.isfinite(d):
            dropped.append((m, "nan_d", n0, n1))
            continue

        lo, hi = boot_ci(x, y)
        if not (np.isfinite(lo) and np.isfinite(hi)):
            dropped.append((m, "nan_ci", n0, n1))
            continue

        rows.append((m, float(d), float(lo), float(hi), n0, n1))

    if not rows:
        print(f"[WARN] effect_forest: no metrics survived for {group_var} ({g0} vs {g1}).")
        print("[WARN] dropped (first 20):", dropped[:20])
        return None

    rows.sort(key=lambda t: abs(t[1]), reverse=True)

    labels = [r[0] for r in rows][::-1]
    dvals  = np.array([r[1] for r in rows], dtype=float)[::-1]
    lo     = np.array([r[2] for r in rows], dtype=float)[::-1]
    hi     = np.array([r[3] for r in rows], dtype=float)[::-1]

    y = np.arange(len(labels))
    plt.figure(figsize=(8, max(3, 0.35 * len(labels))))
    plt.errorbar(dvals, y, xerr=[dvals - lo, hi - dvals], fmt='o', capsize=3)
    plt.yticks(y, labels)
    plt.axvline(0.0)
    plt.title(title or f"Effect sizes by {group_var}: {g0} vs {g1}")
    plt.xlabel(f"Cohen's d ({g0} − {g1})")
    plt.tight_layout()

    path = outdir / "fig4_effect_forest_dataset.png"
    plt.savefig(path, dpi=200)
    plt.close()

    print(f"[effect_forest] groups={g0},{g1} kept={len(rows)} dropped={len(dropped)} min_n={min_n_per_group}")
    print("[effect_forest] dropped (first 20):", dropped[:20])

    return path


def fig_audit(df, outdir: Path):
    cols = ["needs_more_context", "used_examples_count", "missing_count", "why_usedfeat_mismatch_rate"]
    avail = [c for c in cols if c in df.columns]
    if not avail:
        return None

    group = "dataset" if "dataset" in df.columns else None

    def summarize(sub):
        n = len(sub)
        return {
            "n": n,
            "needs_more_context_rate": float(np.mean(sub["needs_more_context"].astype(float)))
            if "needs_more_context" in sub
            else np.nan,
            "used_examples_empty_rate": float(
                np.mean((sub["used_examples_count"].fillna(0) == 0).astype(float))
            )
            if "used_examples_count" in sub
            else np.nan,
            "missing_nonzero_rate": float(np.mean((sub["missing_count"].fillna(0) > 0).astype(float)))
            if "missing_count" in sub
            else np.nan,
            "why_usedfeat_mismatch_mean": float(np.nanmean(sub["why_usedfeat_mismatch_rate"]))
            if "why_usedfeat_mismatch_rate" in sub
            else np.nan,
        }

    summary = []
    summary.append(("ALL", summarize(df)))
    if group:
        for g, sub in df.groupby(group):
            summary.append((str(g), summarize(sub)))

    labels = [s[0] for s in summary]
    vals1 = [s[1]["needs_more_context_rate"] for s in summary]
    vals2 = [s[1]["used_examples_empty_rate"] for s in summary]
    vals3 = [s[1]["missing_nonzero_rate"] for s in summary]
    vals4 = [s[1]["why_usedfeat_mismatch_mean"] for s in summary]

    x = np.arange(len(labels))
    width = 0.2

    plt.figure(figsize=(10, 3.6))
    plt.bar(x - 1.5 * width, vals1, width, label="needs_more_context")
    plt.bar(x - 0.5 * width, vals2, width, label="used_examples_empty")
    plt.bar(x + 0.5 * width, vals3, width, label="missing_nonzero")
    plt.bar(x + 1.5 * width, vals4, width, label="why/used_features mismatch (mean)")
    plt.xticks(x, labels)
    plt.ylim(0, 1.0)
    plt.ylabel("rate")
    plt.title("LLM audit / provenance health")
    plt.legend(loc="best", frameon=True)
    plt.tight_layout()

    path = outdir / "figS2_llm_audit.png"
    plt.savefig(path, dpi=200)
    plt.close()
    return path


def fig_case(df, outdir: Path, case_speaker=None, metrics=None):
    metrics = metrics or DEFAULT_METRICS

    if case_speaker is None:
        if "atypicality_v0" in df.columns and df["atypicality_v0"].notna().any():
            idx = df["atypicality_v0"].astype(float).idxmax()
        else:
            idx = df.index[0]
        case = df.loc[idx]
    else:
        sub = df[df["speaker_id"] == case_speaker]
        if sub.empty:
            return None
        case = sub.iloc[0]

    base = df
    if "dataset" in df.columns and pd.notna(case.get("dataset", None)):
        base = df[df["dataset"] == case["dataset"]]
        if base.empty:
            base = df

    vals = []
    for m in metrics:
        if m not in df.columns:
            continue
        x = pd.to_numeric(base[m], errors="coerce").dropna().to_numpy(dtype=float)
        v = float(case.get(m, np.nan))
        if len(x) >= 5 and not np.isnan(v):
            med = float(np.median(x))
            mad = float(np.median(np.abs(x - med)))
            z = (v - med) / (1.4826 * mad) if mad > 0 else np.nan
        else:
            z = np.nan
        vals.append((m, v, z))

    if not vals:
        return None

    labels = [t[0] for t in vals]
    zvals = np.array([t[2] for t in vals], dtype=float)
    use_raw = np.all(np.isnan(zvals))
    plot_vals = np.array([t[1] for t in vals], dtype=float) if use_raw else zvals

    y = np.arange(len(labels))[::-1]
    plt.figure(figsize=(8, max(3, 0.35 * len(labels))))
    plt.barh(y, plot_vals)
    plt.yticks(y, labels)
    plt.axvline(0.0)

    title = f"Case study: {case.get('speaker_id','')}"
    if pd.notna(case.get("primary_label", None)):
        title += f" (primary={case.get('primary_label')} {case.get('primary_conf', '')})"

    plt.title(title + (" [raw]" if use_raw else " [robust z]"))
    plt.xlabel("value" if use_raw else "robust z-score")
    plt.tight_layout()

    path = outdir / "figS1_case_profile.png"
    plt.savefig(path, dpi=200)
    plt.close()
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, help="Input JSONL or JSON array file")
    ap.add_argument("--out", dest="outdir", default="paper_figs", help="Output directory")
    ap.add_argument(
        "--group",
        dest="group_var",
        default="dataset",
        help="Group variable for effect sizes (default: dataset)",
    )
    ap.add_argument("--case-speaker", dest="case_speaker", default=None, help="speaker_id for case study figure")
    ap.add_argument("--min-n-per-group", type=int, default=2, help="Minimum non-null N required in EACH group for a metric to be included in effect-forest.")
    args = ap.parse_args()

    inp = Path(args.inp)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    rows = read_rows(inp)
    df = flatten_rows(rows)

    metric_cols = [c for c in df.columns if c.startswith(("PG_", "FILL_", "IX_", "CL_"))]
    df = ensure_numeric(
        df,
        metric_cols
        + ["atypicality_v0", "primary_conf", "missing_count", "used_examples_count", "why_usedfeat_mismatch_rate"],
    )

    df.to_csv(outdir / "flattened_rows.csv", index=False)

    paths = []
    p = fig_pca(df, outdir)
    if p:
        paths.append(p)

    p = fig_effect_forest(df, outdir, group_var=args.group_var, min_n_per_group=args.min_n_per_group)
    if p:
        paths.append(p)

    p = fig_audit(df, outdir)
    if p:
        paths.append(p)

    p = fig_case(df, outdir, case_speaker=args.case_speaker)
    if p:
        paths.append(p)

    print("Wrote:")
    for p in paths:
        print(" -", p)


if __name__ == "__main__":
    main()
