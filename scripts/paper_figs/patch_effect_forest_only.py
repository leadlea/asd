from __future__ import annotations
import re
import sys
from pathlib import Path

TARGET = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("scripts/paper_figs/make_paper_figures.py")
txt = TARGET.read_text(encoding="utf-8")

# 置換する新しい関数（既存の呼び出しは壊さない：引数は互換）
new_func = r'''
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
'''.lstrip("\n")

# 既存の fig_effect_forest ブロックを丸ごと置換（次の def まで）
pat = r"^def fig_effect_forest\([\s\S]*?(?=^def |\Z)"
m = re.search(pat, txt, flags=re.M)
if not m:
    raise SystemExit("ERROR: def fig_effect_forest(...) block not found")

txt = txt[:m.start()] + new_func + "\n\n" + txt[m.end():]
TARGET.write_text(txt, encoding="utf-8")
print("OK: patched", TARGET)
