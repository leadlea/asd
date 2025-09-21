
import re
import pandas as pd
from pathlib import Path

TOK = re.compile(r"[A-Za-z']+")
CAP = re.compile(r"\b[A-Z][a-z]+\b")
PRON = set("i we you he she they it this that these those".split())

def toks(s: str): 
    return TOK.findall((s or "").lower())

def ref_metrics(utter_csv: str, out_csv: str, speaker_child: str="CHI",
                window:int=10, reintro_gap:int=8):
    df = pd.read_csv(utter_csv)
    # 列名のゆらぎ吸収
    utt_col = "utt_clean" if "utt_clean" in df.columns else ("utt" if "utt" in df.columns else None)
    if utt_col is None:
        raise SystemExit("utter_csv に 'utt_clean' も 'utt' も見つかりません")
    spk_col = "speaker" if "speaker" in df.columns else ("role" if "role" in df.columns else None)
    if spk_col is None:
        raise SystemExit("utter_csv に 'speaker' も 'role' も見つかりません")

    # 子発話のみ（CHI をデフォルト）
    cdf = df[df[spk_col].astype(str).str.upper() == speaker_child.upper()].copy()
    rows=[]
    for fid, g in cdf.groupby("file_id"):
        U = g[utt_col].fillna("").tolist()
        intro=maint=reintro=ambig=0
        seen=set(); last={}
        for i,u in enumerate(U):
            # 固有名詞近似（先頭大文字語から代名詞を除外）
            caps=[w for w in CAP.findall(u) if w.lower() not in PRON]
            for n in [w.lower() for w in caps]:
                if n not in seen:
                    intro += 1; seen.add(n)
                else:
                    gap = i - last.get(n, -10)
                    if gap >= reintro_gap: reintro += 1
                    else: maint += 1
                last[n]=i
            # 曖昧参照近似：代名詞があり、直近windowに候補名詞が無い
            ts = toks(u)
            if any(t in PRON for t in ts):
                recent=set()
                for j in range(max(0, i-window), i):
                    recent |= set(w.lower() for w in CAP.findall(U[j]) if w.lower() not in PRON)
                if not recent:
                    ambig += 1
        Uc = len(U)
        per_utt = (lambda x: round(x / max(1, Uc), 4))
        rows.append({
            "file_id": fid,
            "ref_intro_per_utt": per_utt(intro),
            "ref_maint_per_utt": per_utt(maint),
            "ref_reintro_per_utt": per_utt(reintro),
            "ref_ambig_pron_per_utt": per_utt(ambig),
        })
    out = Path(out_csv); out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out, index=False)
    print("wrote ->", out)

if __name__ == "__main__":
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--utter", required=True, help="utterances CSV (QC後)")
    ap.add_argument("--out", required=True,   help="出力CSV")
    ap.add_argument("--speaker_child", default="CHI")
    ap.add_argument("--window", type=int, default=10)
    ap.add_argument("--reintro_gap", type=int, default=8)
    args=ap.parse_args()
    ref_metrics(args.utter, args.out, args.speaker_child, args.window, args.reintro_gap)
