#!/usr/bin/env python
import pandas as pd
from pathlib import Path

# 解析結果のルート
ROOT_DIAR = Path("out/audio/Nanami")     # 新：pyannote + diar
ROOT_F0   = Path("out_f0/audio/Nanami")  # 旧：F0クラスタ

# 対象セッション（ダッシュボードと揃える）
SESSIONS = ["10129", "10225", "10421", "10622",
            "10928", "11025", "20213", "20319"]


def _load_role_metrics(root: Path, session: str):
    """1セッション分の CHI/MOT 指標を読み込む."""
    sess_dir = root / session

    turns = pd.read_csv(sess_dir / "turns.csv")
    pros  = pd.read_csv(sess_dir / "prosody.csv")
    prag  = pd.read_csv(sess_dir / "pragmatics.csv")

    out = {}

    for role in ("CHI", "MOT"):
        t_row = turns.loc[turns["role"] == role].iloc[0] if (turns["role"] == role).any() else None
        p_row = pros.loc[pros["role"] == role].iloc[0] if (pros["role"] == role).any() else None
        g_row = prag.loc[prag["role"] == role].iloc[0] if (prag["role"] == role).any() else None

        def g(row, col, default=0.0):
            if row is None:
                return default
            return float(row.get(col, default))

        def gi(row, col, default=0):
            if row is None:
                return default
            return int(row.get(col, default))

        m = {
            "n_utts": gi(t_row, "n_utts"),
            "n_tokens": gi(t_row, "n_tokens"),
            "n_types": gi(t_row, "n_types"),
            "mlu": g(t_row, "mlu"),
            "mean_turn_len": g(t_row, "mean_turn_len"),
            "turn_latency_mean": g(t_row, "turn_latency_mean"),
            "f0_mean": g(p_row, "f0_mean"),
            "speech_rate": g(p_row, "speech_rate"),
            "pause_p95": g(p_row, "pause_p95"),
            "question_rate": g(g_row, "question_rate"),
            "dm_per_100t": g(g_row, "dm_per_100t"),
            "mental_per_100t": g(g_row, "mental_per_100t"),
        }
        out[role] = m

    # Token 比（CHI シェア）をあとで入れやすいように返す時に計算
    tot_tokens = out["CHI"]["n_tokens"] + out["MOT"]["n_tokens"]
    if tot_tokens > 0:
        out["CHI"]["token_share"] = out["CHI"]["n_tokens"] / tot_tokens
        out["MOT"]["token_share"] = out["MOT"]["n_tokens"] / tot_tokens
    else:
        out["CHI"]["token_share"] = 0.0
        out["MOT"]["token_share"] = 0.0

    return out


def build_long_table():
    rows = []
    for method, root in [("F0", ROOT_F0), ("DIAR", ROOT_DIAR)]:
        for sess in SESSIONS:
            met = _load_role_metrics(root, sess)
            for role in ("CHI", "MOT"):
                r = {
                    "session": sess,
                    "method": method,
                    "role": role,
                }
                r.update(met[role])
                rows.append(r)
    return pd.DataFrame(rows)


def main():
    df = build_long_table()

    # 1) セッション別 CHI Token シェアの比較
    chi = df[df["role"] == "CHI"][["session", "method", "token_share"]]
    chi_pivot = chi.pivot(index="session", columns="method", values="token_share")
    chi_pivot["DIAR_minus_F0"] = chi_pivot["DIAR"] - chi_pivot["F0"]

    print("\n=== (1) CHI Token シェア比較（セッション別）===")
    print(chi_pivot.round(3))
    print()

    # 2) セッション別の詳細指標（CHI/MOT 並べてみる）
    cols = [
        "n_utts", "n_tokens", "mlu",
        "f0_mean", "speech_rate",
        "question_rate", "dm_per_100t", "mental_per_100t",
    ]
    wide_rows = []
    for sess in SESSIONS:
        row = {"session": sess}
        for method in ("F0", "DIAR"):
            for role in ("CHI", "MOT"):
                sub = df[(df["session"] == sess) &
                         (df["method"] == method) &
                         (df["role"] == role)]
                if sub.empty:
                    continue
                for c in cols:
                    key = f"{method}_{role}_{c}"
                    row[key] = float(sub.iloc[0][c])
        wide_rows.append(row)
    wide = pd.DataFrame(wide_rows).set_index("session")

    print("=== (2) セッション別 詳細比較テーブル（横長）===")
    print(wide.round(2))
    print()

    # 3) 全セッション合計の集計（Token, 発話数など）
    agg = (
        df.groupby(["method", "role"])
          [["n_utts", "n_tokens", "n_types"]]
          .sum()
    )
    print("=== (3) 8セッション合計 指標 ===")
    print(agg)
    print()

    # 4) CSV にも保存しておく（後でダッシュボードに読み込めるように）
    chi_pivot.to_csv("out/audio/nanami_compare_token_share.csv")
    wide.to_csv("out/audio/nanami_compare_detail.csv")
    agg.to_csv("out/audio/nanami_compare_totals.csv")
    print("CSV written to:")
    print("  out/audio/nanami_compare_token_share.csv")
    print("  out/audio/nanami_compare_detail.csv")
    print("  out/audio/nanami_compare_totals.csv")


if __name__ == "__main__":
    main()
