#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ad-hoc regenerator: rebuild the C-ensemble permutation-coef table,
bootstrap-variance table, and bootstrap forest plot from the re-run
(19-feature, topic_drift-excluded) ensemble TSVs.

Usage:
    .venv/bin/python scripts/paper_figs/_regen_coef_bootstrap_rev.py
"""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import gen_paper_figs_v2 as g  # noqa: E402

RESULTS_DIR = Path("artifacts/analysis/results/rev20260706_ensemble")
OUT_DIR = Path("reports/paper_figs_v2")

g.gen_tab_permutation_coef(RESULTS_DIR, OUT_DIR)
print("tab_permutation_coef.tex regenerated")
g.gen_tab_bootstrap_variance(RESULTS_DIR, OUT_DIR)
print("tab_bootstrap_variance.tex regenerated")
g.gen_fig_bootstrap_variance(RESULTS_DIR, OUT_DIR)
print("fig_bootstrap_variance.png regenerated")
