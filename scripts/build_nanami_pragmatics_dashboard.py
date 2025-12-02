#!/usr/bin/env python
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List

import math
import pandas as pd


# ========= 共通ユーティリティ =========

def load_results(results_path: Path) -> pd.DataFrame:
    df = pd.read_csv(results_path)
    required_cols = {"metric_id", "session_id", "speaker_role", "value"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"results CSV is missing columns: {missing}")
    return df


# ========= BASIC_TOKENS_PER_TURN 部分 =========

def load_basic_tokens_summary(df: pd.DataFrame) -> pd.DataFrame:
    """BASIC_TOKENS_PER_TURN を CHI / MOT / BOTH ごとに pivot した表を作る。"""
    sub = df[df["metric_id"] == "BASIC_TOKENS_PER_TURN"].copy()
    pivot = sub.pivot_table(index="session_id", columns="speaker_role", values="value")

    # session_id でソート
    pivot = pivot.sort_index(key=lambda idx: idx.astype(str).astype(int))

    # CHI / MOT / BOTH の列をそろえる（欠けていたら NaN を入れる）
    for col in ["CHI", "MOT", "BOTH"]:
        if col not in pivot.columns:
            pivot[col] = float("nan")

    pivot = pivot[["CHI", "MOT", "BOTH"]]
    pivot = pivot.reset_index()
    return pivot


def compute_stats_for_roles(df_pivot: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    """各 role ごとの min / max / mean / median を計算。"""
    stats: Dict[str, Dict[str, float]] = {}
    for role in ["CHI", "MOT", "BOTH"]:
        if role not in df_pivot.columns:
            continue
        s = df_pivot[role].dropna()
        if s.empty:
            continue
        stats[role] = {
            "min": float(s.min()),
            "max": float(s.max()),
            "mean": float(s.mean()),
            "median": float(s.median()),
        }
    return stats


def build_tokens_rows_html(pivot_df: pd.DataFrame, max_display: float = 40.0) -> str:
    """セッション別トークン密度テーブルの HTML を生成。"""
    rows_html: List[str] = []

    for _, row in pivot_df.iterrows():
        sid = str(row["session_id"])
        chi = float(row["CHI"])
        mot = float(row["MOT"])
        both = float(row["BOTH"])

        def fmt(v: float) -> str:
            return "-" if math.isnan(v) else f"{v:.3f}"

        def width(v: float) -> float:
            if math.isnan(v):
                return 0.0
            return max(0.0, min(1.0, v / max_display)) * 100.0

        chi_w = width(chi)
        mot_w = width(mot)
        both_w = width(both)

        rows_html.append(
            f"""
            <tr>
              <td class="sid">{sid}</td>

              <td class="value">
                <div class="label">CHI</div>
                <div class="num">{fmt(chi)}</div>
              </td>
              <td class="bar-cell">
                <div class="bar-track"><div class="bar chi" style="width:{chi_w:.1f}%;"></div></div>
              </td>

              <td class="value">
                <div class="label">MOT</div>
                <div class="num">{fmt(mot)}</div>
              </td>
              <td class="bar-cell">
                <div class="bar-track"><div class="bar mot" style="width:{mot_w:.1f}%;"></div></div>
              </td>

              <td class="value">
                <div class="label">BOTH</div>
                <div class="num">{fmt(both)}</div>
              </td>
              <td class="bar-cell">
                <div class="bar-track"><div class="bar both" style="width:{both_w:.1f}%;"></div></div>
              </td>
            </tr>
            """
        )

    return "\n".join(rows_html)


def build_stats_cards_html(stats: Dict[str, Dict[str, float]]) -> str:
    """
    BASIC_TOKENS_PER_TURN の min / max / mean / median を
    ミニチャート付きカードとして表示する HTML を生成。
    """

    if not stats:
        return ""

    # 全ロール共通のスケール（min, max）を計算
    global_min = min(v["min"] for v in stats.values())
    global_max = max(v["max"] for v in stats.values())
    if not math.isfinite(global_min) or not math.isfinite(global_max):
        global_min, global_max = 0.0, 1.0
    if global_max <= global_min:
        global_max = global_min + 1e-6

    def pos(value: float) -> float:
        """global_min〜global_max を 0〜100% に線形マッピング。"""
        t = (value - global_min) / (global_max - global_min)
        t = max(0.0, min(1.0, t))
        return t * 100.0

    def block(role: str) -> str:
        s = stats.get(role)
        if not s:
            return ""
        span_left = pos(s["min"])
        span_width = max(3.0, pos(s["max"]) - span_left)
        median_left = pos(s["median"])
        mean_left = pos(s["mean"])
        role_class = role.lower()
        return f"""
        <div class="stat-card">
          <div class="stat-label">{role}</div>
          <div class="stat-main">{s['median']:.2f}</div>
          <div class="stat-sub">
            min {s['min']:.2f} / max {s['max']:.2f} / mean {s['mean']:.2f}
          </div>
          <div class="stat-range">
            <div class="stat-range-track">
              <div class="stat-range-span role-{role_class}" style="left:{span_left:.1f}%;width:{span_width:.1f}%;"></div>
              <div class="stat-marker median" style="left:{median_left:.1f}%;"></div>
              <div class="stat-marker mean" style="left:{mean_left:.1f}%;"></div>
            </div>
            <div class="stat-range-caption">min → max（● median, ◇ mean / 共通スケール）</div>
          </div>
        </div>
        """

    return block("CHI") + block("MOT") + block("BOTH")


# ========= 精神医学系 指標一覧テーブル（CHI/MOT 同セル2段） =========

def build_pragmatics_summary_table(
    df: pd.DataFrame,
    metrics: List[str],
    roles: List[str],
) -> str:
    """
    metrics: 指標IDのリスト
      例: ["TT_GAP_MEAN", "TT_OVERLAP_RATE", ...]
    roles:   ["CHI", "MOT"]
    """
    # すべての session_id を集約
    session_ids = sorted(df["session_id"].unique(), key=lambda x: int(str(x)))

    # (metric, role, session) -> value の辞書
    value_map: Dict[tuple, float] = {}
    for _, row in df.iterrows():
        key = (str(row["metric_id"]), str(row["speaker_role"]), str(row["session_id"]))
        value_map[key] = float(row["value"])

    # ヘッダ：指標ごとに1列
    header_cells = ["<th>session_id</th>"]
    for metric_id in metrics:
        header_cells.append(f"<th>{metric_id}</th>")
    header_html = "<tr>" + "".join(header_cells) + "</tr>"

    # 本文
    body_rows: List[str] = []
    for sid in session_ids:
        sid_str = str(sid)
        row_cells = [f"<td class='sid'>{sid_str}</td>"]
        for metric_id in metrics:
            lines = []
            for role in roles:  # ["CHI", "MOT"]
                v = value_map.get((metric_id, role, sid_str), float("nan"))
                if math.isnan(v):
                    txt = "-"
                else:
                    if metric_id in ("TT_OVERLAP_RATE", "QUESTION_RATE"):
                        txt = f"{v:.1f}"
                    elif metric_id in ("SPEECH_RATE",):
                        txt = f"{v:.2f}"
                    else:
                        txt = f"{v:.2f}"
                lines.append(f"{role} {txt}")
            cell_html = "<br/>".join(lines)
            row_cells.append(f"<td class='num multi-role'>{cell_html}</td>")
        body_rows.append("<tr>" + "".join(row_cells) + "</tr>")

    body_html = "\n".join(body_rows)

    table_html = f"""
    <div class="table-wrapper">
      <table class="metrics-table">
        <thead>
          {header_html}
        </thead>
        <tbody>
          {body_html}
        </tbody>
      </table>
    </div>
    """
    return table_html


# ========= 指標×セッション ヒートマップ =========

def build_pragmatics_heatmap(
    df: pd.DataFrame,
    metrics: List[str],
    roles: List[str],
) -> str:
    session_ids = sorted(df["session_id"].unique(), key=lambda x: int(str(x)))

    # (metric, role, session) -> value
    value_map: Dict[tuple, float] = {}
    for _, row in df.iterrows():
        key = (str(row["metric_id"]), str(row["speaker_role"]), str(row["session_id"]))
        value_map[key] = float(row["value"])

    # metric×roleごとの min/max
    ranges: Dict[tuple, tuple] = {}
    for metric_id in metrics:
        for role in roles:
            vals = []
            for sid in session_ids:
                v = value_map.get((metric_id, role, str(sid)), float("nan"))
                if not math.isnan(v):
                    vals.append(v)
            if vals:
                vmin = min(vals)
                vmax = max(vals)
            else:
                vmin, vmax = float("nan"), float("nan")
            ranges[(metric_id, role)] = (vmin, vmax)

    def color_for(metric_id: str, role: str, sid: str) -> str:
        v = value_map.get((metric_id, role, sid), float("nan"))
        vmin, vmax = ranges[(metric_id, role)]
        if math.isnan(v) or math.isnan(vmin) or math.isnan(vmax) or vmax <= vmin:
            return "#f9fafb"
        t = (v - vmin) / (vmax - vmin)
        t = max(0.0, min(1.0, t))
        # 明るいラベンダー → 濃いパープル
        lightness = 92 - 40 * t
        return f"hsl(245, 85%, {lightness:.1f}%)"

    def label_for(metric_id: str, role: str, sid: str) -> str:
        v = value_map.get((metric_id, role, sid), float("nan"))
        if math.isnan(v):
            return "-"
        if metric_id in ("TT_OVERLAP_RATE", "QUESTION_RATE"):
            return f"{v:.1f}"
        elif metric_id in ("SPEECH_RATE",):
            return f"{v:.2f}"
        else:
            return f"{v:.2f}"

    tables_html: List[str] = []
    for role in roles:
        # ヘッダ
        header_cells = ["<th>metric_id</th>"]
        for sid in session_ids:
            header_cells.append(f"<th>{sid}</th>")
        header_html = "<tr>" + "".join(header_cells) + "</tr>"

        # 本文
        body_rows: List[str] = []
        for metric_id in metrics:
            row_cells = [f"<td class='sid'>{metric_id}</td>"]
            for sid in session_ids:
                sid_str = str(sid)
                color = color_for(metric_id, role, sid_str)
                label = label_for(metric_id, role, sid_str)
                row_cells.append(
                    f"<td class='heatmap-cell' style='background:{color};'>{label}</td>"
                )
            body_rows.append("<tr>" + "".join(row_cells) + "</tr>")

        body_html = "\n".join(body_rows)
        table_html = f"""
        <div class="heatmap-panel">
          <div class="heatmap-title">{role}</div>
          <div class="heatmap-table-wrapper">
            <table class="heatmap-table">
              <thead>{header_html}</thead>
              <tbody>{body_html}</tbody>
            </table>
          </div>
        </div>
        """
        tables_html.append(table_html)

    return "<div class='heatmap-grid'>" + "".join(tables_html) + "</div>"


# ========= HTML 全体 =========

def build_html(
    tokens_pivot: pd.DataFrame,
    stats_basic: Dict[str, Dict[str, float]],
    df_all: pd.DataFrame,
) -> str:
    tokens_rows_html = build_tokens_rows_html(tokens_pivot, max_display=40.0)
    stats_html = build_stats_cards_html(stats_basic)

    # 会話タイミング・フィラー・質問・プロソディ + 終助詞プロファイル + 応答パターン
    metrics_for_prag = [
        # ターン交替・フィラー・質問
        "TT_GAP_MEAN",
        "TT_OVERLAP_RATE",
        "FILLER_RATE",
        "QUESTION_RATE",
        "SFP_NEGOTIATING_RATE",
        # 終助詞プロファイル
        "SFP_NE_RATE",
        "SFP_NE_Q_RATE",
        "SFP_YO_RATE",
        "SFP_NA_RATE",
        "SFP_NO_RATE",
        "SFP_MON_RATE",
        # 応答パターン
        "RESP_NE_AIZUCHI_RATE",
        "RESP_NE_ENTROPY",
        "RESP_YO_ENTROPY",
        # プロソディ
        "SPEECH_RATE",
        "PAUSE_RATIO",
        "F0_SD",
    ]

    prag_table_html = build_pragmatics_summary_table(
        df_all,
        metrics=metrics_for_prag,
        roles=["CHI", "MOT"],
    )

    heatmap_html = build_pragmatics_heatmap(
        df_all,
        metrics=metrics_for_prag,
        roles=["CHI", "MOT"],
    )

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8" />
  <title>Nanami Pragmatics Dashboard – BASIC_TOKENS_PER_TURN + pragmatics (timing / SFP / response / prosody)</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    :root {{
      --bg: #f5f7fb;
      --card-bg: #ffffff;
      --accent: #4f46e5;
      --accent-soft: rgba(79, 70, 229, 0.08);
      --text: #111827;
      --muted: #6b7280;
      --border: #e5e7eb;
      --danger: #ef4444;
      --chi: #6366f1;
      --mot: #22c55e;
      --both: #f97316;
      --font-sans: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 24px;
      font-family: var(--font-sans);
      background: radial-gradient(circle at 0 0, #e0e7ff 0, transparent 45%), var(--bg);
      color: var(--text);
    }}
    .container {{ width: 100%; max-width: 100%; margin: 0 auto; }}
    .header-card {{
      background: linear-gradient(135deg, #4f46e5, #6366f1);
      border-radius: 18px;
      padding: 20px 24px;
      color: white;
      box-shadow: 0 18px 40px rgba(15, 23, 42, 0.28);
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
    }}
    .header-text h1 {{ margin: 0 0 6px; font-size: 20px; letterspacing: 0.04em; }}
    .header-text p {{ margin: 0; font-size: 13px; opacity: 0.9; }}
    .badge {{
      display: inline-flex; align-items: center; gap: 6px;
      padding: 4px 10px; border-radius: 999px;
      background: rgba(15, 23, 42, 0.15);
      font-size: 11px; font-weight: 500;
    }}
    .badge-dot {{
      width: 7px; height: 7px; border-radius: 999px;
      background: #22c55e; box-shadow: 0 0 0 4px rgba(34, 197, 94, 0.4);
    }}
    .main-grid {{
      margin-top: 20px;
      display: grid;
      grid-template-columns: minmax(0, 1.7fr) minmax(0, 1.1fr);
      gap: 16px;
    }}
    @media (max-width: 900px) {{
      .main-grid {{ grid-template-columns: minmax(0, 1fr); }}
    }}
    .card {{
      background: var(--card-bg);
      border-radius: 16px;
      padding: 16px 18px;
      box-shadow: 0 12px 25px rgba(15, 23, 42, 0.08);
      border: 1px solid rgba(148, 163, 184, 0.25);
    }}
    .card-header {{
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 10px;
    }}
    .card-title {{
      font-size: 14px; font-weight: 600;
      display: flex; align-items: center; gap: 8px;
    }}
    .card-title span.icon {{
      display: inline-flex; align-items: center; justify-content: center;
      width: 20px; height: 20px; border-radius: 999px;
      background: var(--accent-soft); color: var(--accent); font-size: 13px;
    }}
    .card-subtitle {{ font-size: 11px; color: var(--muted); }}
    .pill {{
      padding: 3px 10px; border-radius: 999px; font-size: 11px;
      border: 1px solid rgba(148, 163, 184, 0.6);
      color: var(--muted); background: rgba(248, 250, 252, 0.8);
    }}

    .stats-grid {{
      display: grid; grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px; margin-top: 8px;
    }}
    .stat-card {{
      padding: 8px 10px; border-radius: 10px;
      background: var(--accent-soft);
      border: 1px solid rgba(129, 140, 248, 0.5);
    }}
    .stat-label {{ font-size: 11px; color: #4f46e5; font-weight: 600; margin-bottom: 4px; }}
    .stat-main {{ font-size: 16px; font-weight: 600; }}
    .stat-sub {{ font-size: 11px; color: var(--muted); }}

    /* min〜max のレンジ + median / mean のミニチャート */
    .stat-range {{
      margin-top: 6px;
    }}
    .stat-range-track {{
      position: relative;
      height: 10px;
      border-radius: 999px;
      background: #e5e7eb;
      overflow: hidden;
    }}
    .stat-range-span {{
      position: absolute;
      top: 0;
      bottom: 0;
      background: rgba(129, 140, 248, 0.5);
    }}
    .stat-range-span.role-chi {{
      background: rgba(99, 102, 241, 0.7);
    }}
    .stat-range-span.role-mot {{
      background: rgba(34, 197, 94, 0.7);
    }}
    .stat-range-span.role-both {{
      background: rgba(249, 115, 22, 0.7);
    }}
    .stat-marker {{
      position: absolute;
      top: 50%;
      width: 10px;
      height: 10px;
      transform: translate(-50%, -50%);
      border-radius: 999px;
      border: 2px solid #ffffff;
      box-shadow: 0 0 0 1px rgba(15, 23, 42, 0.3);
    }}
    .stat-marker.median {{
      background: #111827;
    }}
    .stat-marker.mean {{
      background: #ffffff;
    }}
    .stat-marker.mean::after {{
      content: "";
      position: absolute;
      inset: 2px;
      border-radius: 999px;
      background: #111827;
    }}
    .stat-range-caption {{
      margin-top: 3px;
      font-size: 10px;
      color: var(--muted);
    }}

    .table-wrapper {{
      margin-top: 4px; max-height: 420px; overflow: auto;
      border-radius: 10px;
      border: 1px solid rgba(148, 163, 184, 0.6);
      background: #f9fafb;
    }}
    table {{ width: 100%; border-collapse: collapse; font-size: 11px; }}
    thead {{ background: #eef2ff; position: sticky; top: 0; z-index: 1; }}
    th, td {{
      padding: 6px 10px; border-bottom: 1px solid var(--border);
      white-space: nowrap;
    }}
    th {{ text-align: left; }}
    td.sid {{ font-weight: 600; }}
    tbody tr:nth-child(even) {{ background: #f9fafb; }}

    td.value {{ width: 80px; vertical-align: top; }}
    .label {{ font-size: 10px; color: var(--muted); }}
    .num {{ font-size: 12px; font-weight: 600; }}

    td.bar-cell {{ width: 120px; vertical-align: middle; }}
    .bar-track {{
      width: 100%; height: 6px; border-radius: 999px;
      background: #e5e7eb; overflow: hidden;
    }}
    .bar {{
      height: 100%; border-radius: 999px;
    }}
    .bar.chi {{ background: var(--chi); }}
    .bar.mot {{ background: var(--mot); }}
    .bar.both {{ background: var(--both); }}

    .legend {{
      display: flex; gap: 10px; flex-wrap: wrap; margin-top: 6px;
      font-size: 11px; color: var(--muted);
    }}
    .legend-item {{ display: inline-flex; align-items: center; gap: 4px; }}
    .legend-swatch {{
      width: 10px; height: 10px; border-radius: 999px;
    }}

    .footer-note {{ margin-top: 12px; font-size: 11px; color: var(--muted); }}
    code {{
      font-size: 11px; background: rgba(15, 23, 42, 0.06);
      padding: 2px 5px; border-radius: 4px;
    }}

    .metrics-table td.multi-role {{
      line-height: 1.35;
      font-size: 11px;
    }}

    /* Heatmap styles */
    .heatmap-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
      margin-top: 8px;
    }}
    @media (max-width: 900px) {{
      .heatmap-grid {{
        grid-template-columns: minmax(0, 1fr);
      }}
    }}
    .heatmap-panel {{
      background: #f9fafb;
      border-radius: 12px;
      border: 1px solid rgba(148, 163, 184, 0.6);
      padding: 8px 10px;
    }}
    .heatmap-title {{
      font-size: 11px;
      font-weight: 600;
      color: var(--muted);
      margin-bottom: 6px;
    }}
    .heatmap-table-wrapper {{
      max-height: 260px;
      overflow: auto;
      border-radius: 8px;
    }}
    .heatmap-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 10px;
    }}
    .heatmap-table th,
    .heatmap-table td {{
      padding: 4px 6px;
      border-bottom: 1px solid var(--border);
      border-right: 1px solid var(--border);
      white-space: nowrap;
    }}
    .heatmap-table th:last-child,
    .heatmap-table td:last-child {{
      border-right: none;
    }}
    .heatmap-table thead {{
      background: #e5e7ff;
      position: sticky;
      top: 0;
      z-index: 1;
    }}
    .heatmap-cell {{
      text-align: right;
      font-variant-numeric: tabular-nums;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header-card">
      <div class="header-text">
        <div class="badge">
          <span class="badge-dot"></span>
          Nanami / BASIC_TOKENS_PER_TURN + pragmatics (timing / SFP / response / prosody)
        </div>
        <h1>Nanami Pragmatics Dashboard</h1>
        <p>
          8セッションの母子対話について、<strong>1ターンあたりの平均トークン数</strong>と
          <strong>会話タイミング・フィラー・交渉的終助詞・終助詞プロファイル・終助詞への応答パターン・質問・プロソディ</strong>に関する指標をまとめたダッシュボードです。
        </p>
      </div>
      <div>
        <div style="font-size:12px; text-align:right; opacity:.9;">source: nanami_metric_results.csv</div>
      </div>
    </div>

    <div class="main-grid">
      <div class="card">
        <div class="card-header">
          <div>
            <div class="card-title">
              <span class="icon">📊</span>
              セッション別トークン密度（CHI / MOT / BOTH）
            </div>
            <div class="card-subtitle">
              <code>n_tokens / n_utts</code> に基づく 1ターンあたりの平均トークン数。
              バーの長さは 40 tokens/turn を上限としてクリップしています。
            </div>
          </div>
        </div>

        <div class="legend">
          <div class="legend-item">
            <span class="legend-swatch" style="background:var(--chi);"></span> CHI
          </div>
          <div class="legend-item">
            <span class="legend-swatch" style="background:var(--mot);"></span> MOT
          </div>
          <div class="legend-item">
            <span class="legend-swatch" style="background:var(--both);"></span> BOTH
          </div>
        </div>

        <div class="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>session_id</th>
                <th colspan="2">CHI</th>
                <th colspan="2">MOT</th>
                <th colspan="2">BOTH</th>
              </tr>
            </thead>
            <tbody>
              {tokens_rows_html}
            </tbody>
          </table>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <div>
            <div class="card-title">
              <span class="icon">📐</span>
              BASIC_TOKENS_PER_TURN 記述統計
            </div>
            <div class="card-subtitle">
              CHI / MOT / BOTH ごとの min / max / mean / median を、ミニチャート付きで確認します。
            </div>
          </div>
        </div>
        <div class="stats-grid">
          {stats_html}
        </div>
        <div class="footer-note">
          各カードのレンジバーは、BASIC_TOKENS_PER_TURN 全体の最小値〜最大値を共通スケールとして、
          その中で各話者の min–max 範囲と median / mean の位置関係を示しています。
          会話全体のレンジ感と、CHI/MOT/BOTH の違いを直感的に把握するためのビューです。
        </div>
      </div>
    </div>

    <div class="card" style="margin-top:16px;">
      <div class="card-header">
        <div>
          <div class="card-title">
            <span class="icon">🧠</span>
            精神医学に関連する語用論・プロソディ・終助詞指標サマリ
          </div>
          <div class="card-subtitle">
            ターン交替のタイミング（TT_GAP_MEAN, TT_OVERLAP_RATE）、
            フィラー率（FILLER_RATE）、
            質問率（QUESTION_RATE）、
            交渉的終助詞率（SFP_NEGOTIATING_RATE）に加え、
            終助詞プロファイル（SFP_NE_RATE, SFP_NE_Q_RATE, SFP_YO_RATE, SFP_NA_RATE, SFP_NO_RATE, SFP_MON_RATE）と
            「ね」「よ」への応答パターン（RESP_NE_AIZUCHI_RATE, RESP_NE_ENTROPY, RESP_YO_ENTROPY）、
            プロソディ指標（SPEECH_RATE, PAUSE_RATIO, F0_SD）を
            CHI / MOT ごとに 1 セル 2 段で一覧表示します。
          </div>
        </div>
      </div>
      {prag_table_html}
      <div class="footer-note">
        <strong>単位:</strong>
        <code>TT_GAP_MEAN</code> = 秒,
        <code>TT_OVERLAP_RATE</code> = %, 
        <code>FILLER_RATE</code> = フィラー出現数 / 100トークン,
        <code>SFP_NEGOTIATING_RATE</code> = 交渉的な終助詞を含むターン数 / 100ターン,
        <code>QUESTION_RATE</code> = 質問とみなされたターン数 / 100ターン,<br/>
        <code>SFP_NE_RATE</code>, <code>SFP_NE_Q_RATE</code>, <code>SFP_YO_RATE</code>,
        <code>SFP_NA_RATE</code>, <code>SFP_NO_RATE</code>, <code>SFP_MON_RATE</code> =
        文末が各終助詞グループで終わる発話の割合（0〜1 の ratio）,<br/>
        <code>RESP_NE_AIZUCHI_RATE</code> = 「ね」系終助詞（NE / NE_Q）直後に典型的あいづち語で応答した割合（0〜1 の ratio）,<br/>
        <code>RESP_NE_ENTROPY</code>, <code>RESP_YO_ENTROPY</code> =
        「ね」「よ」に対する応答の 1語目の分布のエントロピー（Shannon entropy, log2, float）,<br/>
        <code>SPEECH_RATE</code> = 発話速度 (per_sec),
        <code>PAUSE_RATIO</code> = ポーズ代表値 (pause_p95 ベース),
        <code>F0_SD</code> = F0 の標準偏差 (Hz)。<br/>
        これらは ASD/TD 間や介入前後の比較など、計算論的精神医学の文脈で有用とされる指標群です。
      </div>
    </div>

    <div class="card" style="margin-top:16px;">
      <div class="card-header">
        <div>
          <div class="card-title">
            <span class="icon">🌡️</span>
            指標 × セッション ヒートマップ
          </div>
          <div class="card-subtitle">
            各指標ごとに、CHI / MOT それぞれのセッション間の相対的な高さを色で可視化します。
            濃い色ほど、その話者・指標において値が高いセッションです。
          </div>
        </div>
      </div>
      {heatmap_html}
      <div class="footer-note">
        指標ごとに min–max で線形に正規化した値をもとに色を付けています。
        絶対値というよりも、「どのセッションが相対的に高い/低いか」を眺めるためのビューです。
      </div>
    </div>
  </div>
</body>
</html>
"""
    return html


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build Nanami pragmatics HTML dashboard with heatmap."
    )
    parser.add_argument(
        "--results",
        type=Path,
        default=Path("out/audio/Nanami/nanami_metric_results.csv"),
        help="nanami_metric_results.csv へのパス",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("out/audio/Nanami/Nanami_pragmatics_basic.html"),
        help="生成するHTMLのパス",
    )
    args = parser.parse_args()

    df = load_results(args.results)
    tokens_pivot = load_basic_tokens_summary(df)
    stats = compute_stats_for_roles(tokens_pivot)

    html = build_html(tokens_pivot, stats, df)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html, encoding="utf-8")
    print(f"[INFO] wrote dashboard to {args.out}")


if __name__ == "__main__":
    main()
