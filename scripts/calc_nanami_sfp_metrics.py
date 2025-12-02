#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Nanami Pragmatics Dashboard 用:
終助詞産出プロファイル + 応答パターン指標を nanami_metric_results.csv に追記するスクリプト。

(1) out/audio/Nanami/<session_id>/segments.csv を全部読む
(2) 文末終助詞タグを付与
(3) セッション×役割ごとの SFP_*_RATE を計算
(4) 「ね/よ」発話 → 直後の応答 というペアから RESP_* 指標を計算
(5) 既存 nanami_metric_results.csv を読み込んで、上記を追記して書き戻す
"""

import argparse
import math
import os
from collections import Counter

import pandas as pd


# ==========================
# 1. 終助詞タグ付けヘルパ
# ==========================

def detect_sfp(text: str):
    """
    文末の終助詞フォームとグループを簡易に判定する。

    戻り値:
      (sfp_form, sfp_group, is_question_like)
      sfp_form: 実際にマッチした終助詞（例: "ね", "よね", "かな", "もんね" など）or None
      sfp_group: "NE", "NE_Q", "YO", "NA", "NO", "MON", None のいずれか
      is_question_like: True/False（「？」などを含む疑問的な終助詞か）
    """
    if not isinstance(text, str):
        return None, None, False

    orig = text.strip()
    if not orig:
        return None, None, False

    # 疑問符が付いているかどうか
    has_qmark = orig.endswith("？") or orig.endswith("?")

    # 文末の記号を一旦剥がす
    text = orig
    for punct in ["。", "？", "?", "！", "!", "…", "‥"]:
        if text.endswith(punct):
            text = text[:-1]

    # チェック順は長いものから
    sfp_patterns = [
        ("もんね", "MON"),
        ("だよね", "NE"),
        ("だよな", "NA"),
        ("だよ", "YO"),
        ("かな", "NA"),
        ("よね", "NE"),
        ("のね", "NO"),
        ("のよ", "NO"),
        ("よな", "NA"),
        ("もん", "MON"),
        ("だね", "NE"),
        ("ね", "NE"),
        ("よ", "YO"),
        ("な", "NA"),
        ("の", "NO"),
    ]

    sfp_form = None
    sfp_group = None
    for form, group in sfp_patterns:
        if text.endswith(form):
            sfp_form = form
            sfp_group = group
            break

    if sfp_form is None:
        return None, None, False

    # NE_Q 判定（ね系 + 疑問的）
    is_question_like = has_qmark
    sfp_group_final = sfp_group
    if sfp_group == "NE" and is_question_like:
        sfp_group_final = "NE_Q"

    return sfp_form, sfp_group_final, is_question_like


# 典型的なあいづち語のセット（1語目ベース）
AIZUCHI_LEMMAS = {
    "うん", "はい", "ええ", "そう", "そうだ", "そうです",
    "ううん", "いや", "へえ", "ああ"
}


# ==========================
# 2. セグメント読み込み
# ==========================

def load_all_segments(nanami_root: str, corpus_name: str = "Nanami") -> pd.DataFrame:
    """
    out/audio/Nanami/<session_id>/segments.csv をすべて読み込んで結合する。

    - session_id: ディレクトリ名から付与
    - text: 発話テキスト列として必須
    - role: なければ speaker_role / speaker を使って補完し、
            それもなければ 'BOTH' を入れる
    """
    all_rows = []
    for name in sorted(os.listdir(nanami_root)):
        session_dir = os.path.join(nanami_root, name)
        if not os.path.isdir(session_dir):
            continue

        segments_path = os.path.join(session_dir, "segments.csv")
        if not os.path.exists(segments_path):
            continue

        df = pd.read_csv(segments_path)
        df["corpus"] = corpus_name
        df["session_id"] = name  # ディレクトリ名をセッションIDとして使う

        all_rows.append(df)

    if not all_rows:
        raise RuntimeError(f"No segments.csv found under {nanami_root}")

    df_all = pd.concat(all_rows, ignore_index=True)

    # --- 必須カラム（session_id, text）だけ厳密チェック ---
    for col in ["session_id", "text"]:
        if col not in df_all.columns:
            raise RuntimeError(
                f"segments.csv に '{col}' カラムが必要です（コード内で調整してください）。"
            )

    # --- role 列の補完ロジック ---
    if "role" not in df_all.columns:
        if "speaker_role" in df_all.columns:
            df_all["role"] = df_all["speaker_role"]
        elif "speaker" in df_all.columns:
            df_all["role"] = df_all["speaker"]
        else:
            # 最悪のフォールバック：全て BOTH 扱い
            df_all["role"] = "BOTH"

    # 並び順用の start カラム（候補名のうち存在するものを使う）
    for cand in ["start_sec", "start_time", "start", "onset"]:
        if cand in df_all.columns:
            df_all["_sort_time"] = df_all[cand]
            break
    else:
        # なければ元の行順で代用
        df_all["_sort_time"] = df_all.index

    return df_all


# ==========================
# 3. 指標計算
# ==========================

def compute_production_metrics(df_segments: pd.DataFrame) -> pd.DataFrame:
    """
    SFP_NE_RATE, SFP_NE_Q_RATE, SFP_YO_RATE, SFP_NA_RATE, SFP_NO_RATE, SFP_MON_RATE
    をセッション×役割単位で計算。
    """
    metrics = []

    group_cols = ["session_id", "role"]
    grouped = df_segments.groupby(group_cols, dropna=False)

    for (session_id, role), g in grouped:
        n_seg = len(g)
        if n_seg == 0:
            continue

        counts = g["sfp_group"].value_counts(dropna=True)

        def rate_for(name):
            return float(counts.get(name, 0)) / float(n_seg)

        val_ne = rate_for("NE") + rate_for("NE_Q")
        val_ne_q = rate_for("NE_Q")
        val_yo = rate_for("YO")
        val_na = rate_for("NA")
        val_no = rate_for("NO")
        val_mon = rate_for("MON")

        metric_values = {
            "SFP_NE_RATE": (val_ne, "ratio"),
            "SFP_NE_Q_RATE": (val_ne_q, "ratio"),
            "SFP_YO_RATE": (val_yo, "ratio"),
            "SFP_NA_RATE": (val_na, "ratio"),
            "SFP_NO_RATE": (val_no, "ratio"),
            "SFP_MON_RATE": (val_mon, "ratio"),
        }

        for metric_id, (value, unit) in metric_values.items():
            metrics.append(
                {
                    "metric_id": metric_id,
                    "session_id": session_id,
                    "speaker_role": role,
                    "value": value,
                    "unit": unit,
                    "notes": "computed from segments.csv (sentence-final particles)",
                }
            )

    return pd.DataFrame(metrics)


def build_response_pairs(df_segments: pd.DataFrame) -> pd.DataFrame:
    """
    同一セッション内での連続する2発話のペアを作り、
    「前発話の終助詞グループ」と「次発話の1語目」を対応づける。
    """
    # セッションごと・時間順にソート
    df_sorted = df_segments.sort_values(["session_id", "_sort_time"]).reset_index(drop=True)

    rows = []
    for i in range(len(df_sorted) - 1):
        cur = df_sorted.iloc[i]
        nxt = df_sorted.iloc[i + 1]

        if cur["session_id"] != nxt["session_id"]:
            continue

        # 同一話者（role）同士はスキップ（ターン交替を見たい）
        if cur["role"] == nxt["role"]:
            continue

        prev_sfp_group = cur.get("sfp_group", None)
        if pd.isna(prev_sfp_group) or prev_sfp_group is None:
            continue

        # 次発話の1語目トークンを取得
        first_token = ""
        if "tokens" in nxt and isinstance(nxt["tokens"], str) and nxt["tokens"].strip():
            first_token = nxt["tokens"].split()[0]
        else:
            text = str(nxt.get("text", "")).strip()
            # 空白区切りを試す → だめなら先頭文字
            if " " in text:
                first_token = text.split()[0]
            else:
                first_token = text[:1] if text else ""

        rows.append(
            {
                "session_id": cur["session_id"],
                "prev_role": cur["role"],
                "prev_sfp_group": prev_sfp_group,
                "next_role": nxt["role"],
                "next_first_token": first_token,
            }
        )

    if not rows:
        return pd.DataFrame(
            columns=["session_id", "prev_role", "prev_sfp_group", "next_role", "next_first_token"]
        )

    return pd.DataFrame(rows)


def compute_response_metrics(df_pairs: pd.DataFrame) -> pd.DataFrame:
    """
    RESP_NE_AIZUCHI_RATE, RESP_NE_ENTROPY, RESP_YO_ENTROPY
    をセッション×応答側役割単位で計算。
    """
    metrics = []

    group_cols = ["session_id", "next_role"]
    grouped = df_pairs.groupby(group_cols, dropna=False)

    for (session_id, role), g in grouped:
        # NE に対する応答
        g_ne = g[g["prev_sfp_group"].isin(["NE", "NE_Q"])]
        n_ne = len(g_ne)

        # YO に対する応答
        g_yo = g[g["prev_sfp_group"] == "YO"]
        n_yo = len(g_yo)

        # NE: あいづち率 + エントロピー
        if n_ne > 0:
            # あいづち率
            n_aizuchi = sum(
                1 for t in g_ne["next_first_token"].astype(str)
                if t in AIZUCHI_LEMMAS
            )
            resp_ne_aizuchi_rate = float(n_aizuchi) / float(n_ne)

            # エントロピー
            counts_ne = Counter(g_ne["next_first_token"].astype(str))
            total_ne = float(sum(counts_ne.values()))
            h_ne = 0.0
            for c in counts_ne.values():
                p = c / total_ne
                h_ne -= p * math.log2(p)

            metrics.append(
                {
                    "metric_id": "RESP_NE_AIZUCHI_RATE",
                    "session_id": session_id,
                    "speaker_role": role,
                    "value": resp_ne_aizuchi_rate,
                    "unit": "ratio",
                    "notes": "aizuchi rate after NE/NE_Q SFP (from segments.csv)",
                }
            )
            metrics.append(
                {
                    "metric_id": "RESP_NE_ENTROPY",
                    "session_id": session_id,
                    "speaker_role": role,
                    "value": h_ne,
                    "unit": "float",
                    "notes": "entropy of response first tokens after NE/NE_Q SFP (from segments.csv)",
                }
            )

        # YO: エントロピーのみ
        if n_yo > 0:
            counts_yo = Counter(g_yo["next_first_token"].astype(str))
            total_yo = float(sum(counts_yo.values()))
            h_yo = 0.0
            for c in counts_yo.values():
                p = c / total_yo
                h_yo -= p * math.log2(p)

            metrics.append(
                {
                    "metric_id": "RESP_YO_ENTROPY",
                    "session_id": session_id,
                    "speaker_role": role,
                    "value": h_yo,
                    "unit": "float",
                    "notes": "entropy of response first tokens after YO SFP (from segments.csv)",
                }
            )

    if not metrics:
        return pd.DataFrame(
            columns=["metric_id", "session_id", "speaker_role", "value", "unit", "notes"]
        )

    return pd.DataFrame(metrics)


# ==========================
# 4. メイン
# ==========================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--nanami-root",
        required=True,
        help="out/audio/Nanami のパス",
    )
    parser.add_argument(
        "--metrics-in",
        required=True,
        help="既存 nanami_metric_results.csv のパス",
    )
    parser.add_argument(
        "--metrics-out",
        required=True,
        help="新しい nanami_metric_results.csv の出力パス（同じでも可）",
    )
    args = parser.parse_args()

    # 既存メトリクスを読み込み
    df_metrics_in = pd.read_csv(args.metrics_in)

    # segments.csv を全部読み込み
    df_segments = load_all_segments(args.nanami_root)

    # 文末終助詞タグ付け
    sfp_forms = []
    sfp_groups = []
    is_q_list = []
    for text in df_segments["text"]:
        form, group, is_q = detect_sfp(text)
        sfp_forms.append(form)
        sfp_groups.append(group)
        is_q_list.append(is_q)

    df_segments["sfp_form"] = sfp_forms
    df_segments["sfp_group"] = sfp_groups
    df_segments["is_question_like"] = is_q_list

    # 産出指標
    df_prod = compute_production_metrics(df_segments)

    # 応答ペア & 応答指標
    df_pairs = build_response_pairs(df_segments)
    df_resp = compute_response_metrics(df_pairs)

    # 結合
    frames = [df_metrics_in]
    if len(df_prod) > 0:
        frames.append(df_prod)
    if len(df_resp) > 0:
        frames.append(df_resp)

    df_all = pd.concat(frames, ignore_index=True)

    df_all.to_csv(args.metrics_out, index=False)
    print(f"Saved merged metrics to {args.metrics_out}")


if __name__ == "__main__":
    main()
