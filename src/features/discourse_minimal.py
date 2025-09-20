# src/features/discourse_minimal.py
from __future__ import annotations
import argparse, pathlib, re
import pandas as pd
import spacy

def load_nlp():
    try:
        return spacy.load("en_core_web_sm", disable=["ner","textcat"])
    except OSError:
        raise SystemExit("Run: python -m spacy download en_core_web_sm")

def content_lemmas(doc):
    return [t.lemma_.lower() for t in doc
            if not (t.is_space or t.is_punct or t.is_stop) and t.pos_ in {"NOUN","PROPN","VERB","ADJ"}]

def jaccard(a:set, b:set) -> float:
    if not a and not b: return 1.0
    if not a or not b:  return 0.0
    inter = len(a & b); union = len(a | b)
    return inter/union if union else 0.0

def ref_tags(doc):
    # 参照判定に使う簡易集合
    nouns = [t.lemma_.lower() for t in doc if t.pos_=="NOUN"]
    propn = [t.lemma_.lower() for t in doc if t.pos_=="PROPN"]
    prons = [t.lemma_.lower() for t in doc if t.pos_=="PRON"]
    return nouns, propn, prons

def per_file(df_file: pd.DataFrame, nlp, window:int=3) -> dict:
    # df_file: rows of one file_id, columns: speaker, utt
    # 並び順を保持（chat_to_csv.pyの順）
    docs = [nlp(str(u)) for u in df_file["utt"].tolist()]
    speakers = df_file["speaker"].tolist()

    # ---- topic maintenance（CHIのみで評価）----
    chi_idx = [i for i,s in enumerate(speakers) if s=="CHI"]
    chi_jaccs = []
    prev_set = None
    for i in chi_idx:
        lem = set(content_lemmas(docs[i]))
        if prev_set is not None:
            chi_jaccs.append(jaccard(prev_set, lem))
        prev_set = lem
    topic_cohesion_mean = sum(chi_jaccs)/len(chi_jaccs) if chi_jaccs else 0.0
    topic_switch_rate   = sum(1 for x in chi_jaccs if x < 0.1)/len(chi_jaccs) if chi_jaccs else 0.0

    # ---- reference（CHIのみでカウント）----
    seen_recent: list[str] = []   # 直近windowの名詞・固有名
    seen_all: set[str] = set()    # 通史
    ref_intro = ref_maint = ref_reintro = 0
    chi_tokens = 0

    for i in chi_idx:
        doc = docs[i]
        nouns, propn, prons = ref_tags(doc)
        toks = [t for t in doc if not (t.is_space or t.is_punct)]
        chi_tokens += max(1, len(toks))

        # recent set
        recent_set = set(seen_recent[-500:])  # 安全に制限
        cur_mentions = set(nouns + propn)

        # 導入：recentに無い名詞/固有名が出現
        if any(m not in recent_set for m in cur_mentions):
            ref_intro += 1
        # 維持：recentに参照がありpronで受ける（ラフ判定：pronがあれば維持とみなす）
        if prons and recent_set:
            ref_maint += 1
        # 再導入：recentには無いが過去seen_allにはある
        if any((m not in recent_set) and (m in seen_all) for m in cur_mentions):
            ref_reintro += 1

        # update windows
        seen_recent.extend(list(cur_mentions))
        seen_recent = seen_recent[-(window*50):]  # 適当な上限
        seen_all |= cur_mentions

    ref_intro_rate    = ref_intro / max(1, len(chi_idx))
    ref_maint_rate    = ref_maint / max(1, len(chi_idx))
    ref_reintro_rate  = ref_reintro / max(1, len(chi_idx))

    # ---- turn-taking（全体で評価）----
    alt = 0; total_bound = 0
    for a,b in zip(speakers, speakers[1:]):
        total_bound += 1
        if a!=b: alt += 1
    turn_alt_ratio = alt/max(1,total_bound)

    # INVの疑問直後にCHIが出た割合
    resp_to_question = 0; q_total = 0
    for i in range(len(docs)-1):
        if speakers[i]=="INV" and ("?" in df_file["utt"].iloc[i]):
            q_total += 1
            if speakers[i+1]=="CHI":
                resp_to_question += 1
    resp_to_question_rate = resp_to_question/max(1,q_total)

    # CHI平均トークン長
    chi_lens = []
    for i in chi_idx:
        toks = [t for t in docs[i] if not (t.is_space or t.is_punct)]
        chi_lens.append(len(toks))
    mean_turn_len_chi = sum(chi_lens)/len(chi_lens) if chi_lens else 0.0

    return dict(
        topic_cohesion_mean=topic_cohesion_mean,
        topic_switch_rate=topic_switch_rate,
        ref_intro_rate=ref_intro_rate,
        ref_maint_rate=ref_maint_rate,
        ref_reintro_rate=ref_reintro_rate,
        turn_alt_ratio=turn_alt_ratio,
        resp_to_question_rate=resp_to_question_rate,
        mean_turn_len_chi=mean_turn_len_chi,
    )

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in_csv", required=True, help="utterances.csv (file_id,speaker,utt)")
    ap.add_argument("--out_csv", required=True, help="output discourse_features.csv")
    ap.add_argument("--window", type=int, default=3)
    args = ap.parse_args()
    nlp = load_nlp()
    df = pd.read_csv(args.in_csv)
    feats = []
    for fid, g in df.groupby("file_id", sort=False):
        d = per_file(g[["speaker","utt"]], nlp, window=args.window)
        d["file_id"] = fid
        feats.append(d)
    out = pd.DataFrame(feats)
    pathlib.Path(args.out_csv).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out_csv, index=False)
    print("wrote", args.out_csv, out.shape)

if __name__ == "__main__":
    main()
