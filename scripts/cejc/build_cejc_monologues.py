import argparse, re
import pandas as pd
import numpy as np

def clean_cejc_text(s: str) -> str:
    if s is None:
        return ""
    t = str(s)

    # CEJCのタグっぽい "(L ...)", "(D ...)", "(U ...)" など：タグ文字だけ剥がして中身は残す
    # 例: (L (D ム))(L)(L 落ち武者は(U 何/何人)) -> ム 落ち武者は 何/何人
    t = re.sub(r"\(([A-Z]{1,3})\s*", "", t)   # "(L " "(D " "(U " を削除
    t = t.replace(")", " ")                  # 閉じ括弧だけ消す（中身は残す）

    # 連続空白の圧縮
    t = re.sub(r"\s+", " ", t).strip()
    return t

def load_ids(path: str):
    ids = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            x = line.strip()
            if x:
                ids.append(x)
    return set(ids)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--utterances_parquet", required=True)
    ap.add_argument("--ids_txt", required=True)
    ap.add_argument("--out_parquet", required=True)
    ap.add_argument("--one_per_conv", action="store_true", help="各会話で最優勢話者のみ残す")
    ap.add_argument("--dominance_min", type=float, default=0.0, help="優勢度（発話時間比）の下限")
    ap.add_argument("--min_chars", type=int, default=200, help="連結テキストが短すぎる話者を除外")
    args = ap.parse_args()

    ids = load_ids(args.ids_txt)
    u = pd.read_parquet(args.utterances_parquet)

    # 必須列チェック
    need = ["conversation_id","speaker_id","start_time","end_time","text"]
    miss = [c for c in need if c not in u.columns]
    if miss:
        raise SystemExit(f"utterances missing columns: {miss}")

    u = u[u["conversation_id"].isin(ids)].copy()
    if len(u) == 0:
        raise SystemExit("no utterances after filtering by ids")

    # duration
    st = pd.to_numeric(u["start_time"], errors="coerce").fillna(0.0)
    et = pd.to_numeric(u["end_time"], errors="coerce").fillna(st)
    dur = (et - st).clip(lower=0.0)
    u["_dur"] = dur

    # text clean
    u["_t"] = u["text"].map(clean_cejc_text)

    # speaker total dur per conv
    g = (u.groupby(["conversation_id","speaker_id"], as_index=False)
           .agg(speaker_dur=("_dur","sum"),
                n_utt=("_t","count")))

    conv_total = (u.groupby("conversation_id", as_index=False)
                    .agg(total_dur=("_dur","sum")))
    g = g.merge(conv_total, on="conversation_id", how="left")
    g["dominance"] = np.where(g["total_dur"]>0, g["speaker_dur"]/g["total_dur"], 0.0)

    # 連結テキスト（時系列）
    u = u.sort_values(["conversation_id","speaker_id","start_time","end_time"])
    joined = (u.groupby(["conversation_id","speaker_id"])["_t"]
                .apply(lambda xs: "\n".join([x for x in xs if x]))
                .reset_index()
                .rename(columns={"_t":"text"}))

    out = g.merge(joined, on=["conversation_id","speaker_id"], how="left")
    out["text"] = out["text"].fillna("")
    out["n_chars"] = out["text"].map(len)

    # 最低文字数フィルタ
    out = out[out["n_chars"] >= int(args.min_chars)].copy()

    # dominance フィルタ
    if args.dominance_min and args.dominance_min > 0:
        out = out[out["dominance"] >= float(args.dominance_min)].copy()

    # 各会話1人にする
    if args.one_per_conv:
        out = (out.sort_values(["conversation_id","dominance"], ascending=[True, False])
                 .groupby("conversation_id", as_index=False)
                 .head(1)
                 .copy())

    out = out.sort_values(["conversation_id","dominance"], ascending=[True, False])
    out.to_parquet(args.out_parquet, index=False)

    print("OK:", args.out_parquet)
    print("conversations:", out["conversation_id"].nunique(), "rows(conv×speaker):", len(out))
    print(out[["conversation_id","speaker_id","dominance","speaker_dur","total_dur","n_utt","n_chars"]].head(20).to_string(index=False))
    if len(out):
        print("dominance summary:")
        print(out["dominance"].describe().to_string())

if __name__ == "__main__":
    main()
