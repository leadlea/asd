# -*- coding: utf-8 -*-
"""
Pragmatics Basic features (low-cost), with two outputs:
  A) speaker summary (legacy): CHI/MOT aggregated over all data -> --out_csv
  B) child-group summary (NEW): CHI per dyad -> ASD/TYP means -> --group_out_csv

Inputs:
  --in_csv: utterances.csv (needs: speaker, one of {text, utterance, utt}; optional keys like dyad_id/child_uid/file)
  --dyads : dyads.csv with a join key (e.g., dyad_id/child_uid/file) and a group column (diagnostic_group/group/dx/...)
Outputs:
  --out_csv       : speaker-level summary (kept for backward-compat)
  --group_out_csv : child (CHI) ASD/TYP summary

You can override join keys:
  --utter_key child_uid --dyads_key child_uid
Or rely on auto-detection priority:
  dyad_id -> child_uid -> mother_uid -> file
"""
import re, argparse
import pandas as pd

WH_RE = re.compile(r'^\s*(who|what|why|how|when|where|which|whose)\b', re.I)
QMARK_RE = re.compile(r'\?\s*$')
TOKEN_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")

DM_LEX = {
    "fill":     [r"you know", r"i mean", r"well", r"like"],
    "contrast": [r"but", r"however", r"though", r"although"],
    "causal":   [r"because", r"so\b", r"therefore", r"thus", r"since\b"],
    "shift":    [r"anyway", r"by the way", r"now,", r"ok,", r"okay,"],
}
DM_PAT = {k: re.compile(r"\b(?:%s)\b" % "|".join(v), re.I) for k, v in DM_LEX.items()}

MS_VERBS = {"think","know","believe","guess","remember","forget","feel","want","hope",
            "pretend","notice","decide","understand","suppose","realize","wish","doubt"}
MS_ADJS  = {"sure","afraid","glad","sorry","certain","uncertain","anxious","confident"}
MS_NOUNS = {"idea","plan","belief","memory","thought","feeling","desire","hope"}

JOIN_ALIASES = {
    "dyad_id":   ["dyad_id","dyad","dyad_uid","pair_id","pair_uid","family_id"],
    "child_uid": ["child_uid","child_id","chi_uid","chi_id","participant_child_uid","participant_uid","child","chi"],
    "mother_uid":["mother_uid","mom_uid","mother_id","mom_id","mot_uid","mot_id","mother","mot"],
    "file":      ["file","filename","transcript","cha_file","path","file_id"],
}
JOIN_PRIORITY = ["dyad_id","child_uid","mother_uid","file"]

def pick_text_col(df):
    for c in ["text","utterance","utt"]:
        if c in df.columns: return c
    raise ValueError("Input must contain one of: text/utterance/utt")

def count_tokens(s: str) -> int:
    return len(TOKEN_RE.findall(s or ""))

def ms_counts(text: str):
    toks = [t.lower() for t in TOKEN_RE.findall(text or "")]
    v = sum(t in MS_VERBS for t in toks)
    a = sum(t in MS_ADJS for t in toks)
    n = sum(t in MS_NOUNS for t in toks)
    return v, a, n

def dm_hits(cat: str, text: str) -> int:
    return len(DM_PAT[cat].findall(text or ""))

def per100(x, base, eps=1e-9): return 100.0 * x / (base + eps)

def add_per_utt_flags(df, text_col):
    df["text_"] = df[text_col].fillna("").astype(str)
    df["is_whq"]   = df["text_"].str.match(WH_RE)
    df["is_qmark"] = df["text_"].str.contains(QMARK_RE)
    df["is_ynq"]   = df["is_qmark"] & (~df["is_whq"])
    df["is_q_any"] = df["is_whq"] | df["is_ynq"]
    for k in DM_PAT:
        df[f"dm_{k}_count"] = df["text_"].apply(lambda s: dm_hits(k, s))
    df["tok_n"] = df["text_"].apply(count_tokens)
    ms = df["text_"].apply(ms_counts)
    df["ms_v"], df["ms_a"], df["ms_n"] = zip(*ms)
    df["ms_total"] = df["ms_v"] + df["ms_a"] + df["ms_n"]
    return df

def speaker_summary(df):
    rows = []
    for spk, g in df.groupby("speaker", dropna=False):
        if spk not in ("CHI","MOT"): continue
        n_utt = len(g); n_tok = int(g["tok_n"].sum())
        rows.append({
            "speaker": spk,
            f"{spk}_q_all_rate": g["is_q_any"].mean(),
            f"{spk}_q_wh_rate":  g["is_whq"].mean(),
            f"{spk}_q_yn_rate":  g["is_ynq"].mean(),
            f"{spk}_dm_fill_per100utt":     per100(int(g["dm_fill_count"].sum()), n_utt),
            f"{spk}_dm_contrast_per100utt": per100(int(g["dm_contrast_count"].sum()), n_utt),
            f"{spk}_dm_causal_per100utt":   per100(int(g["dm_causal_count"].sum()), n_utt),
            f"{spk}_dm_shift_per100utt":    per100(int(g["dm_shift_count"].sum()), n_utt),
            f"{spk}_ms_v_per100w":     per100(int(g["ms_v"].sum()), n_tok),
            f"{spk}_ms_a_per100w":     per100(int(g["ms_a"].sum()), n_tok),
            f"{spk}_ms_n_per100w":     per100(int(g["ms_n"].sum()), n_tok),
            f"{spk}_ms_total_per100w": per100(int(g["ms_total"].sum()), n_tok),
            f"{spk}_utt_n": n_utt, f"{spk}_tok_n": n_tok,
        })
    return pd.DataFrame(rows).set_index("speaker")

def detect_join_keys(utt_cols, dy_cols, prefer=None):
    # explicit override
    if prefer and prefer[0] in utt_cols and prefer[1] in dy_cols:
        return prefer[0], prefer[1], "explicit"
    # auto detection across alias families in priority order
    for fam in JOIN_PRIORITY:
        u_alias = next((a for a in JOIN_ALIASES[fam] if a in utt_cols), None)
        d_alias = next((a for a in JOIN_ALIASES[fam] if a in dy_cols), None)
        if u_alias and d_alias:
            return u_alias, d_alias, fam
    return None, None, None

def normalize_group(val: str) -> str:
    if val is None: return ""
    s = str(val).strip().lower()
    if "asd" in s or "autis" in s:
        return "ASD"
    if s in {"td","typ","typical","control","ctl"} or "typ" in s:
        return "TYP"
    return s.upper()  # best-effort

def child_group_summary(df_chi, dyads, join_u, join_d, group_col):
    # join key must exist
    if join_u not in df_chi.columns or join_d not in dyads.columns or group_col not in dyads.columns:
        return pd.DataFrame()
    # dyad-level features
    cols_dm = ["fill","contrast","causal","shift"]
    dy_rows = []
    for key, g in df_chi.groupby(join_u):
        n_utt = len(g); n_tok = int(g["tok_n"].sum())
        out = {join_u: key}
        out.update({
            "q_all_rate": g["is_q_any"].mean(),
            "q_wh_rate":  g["is_whq"].mean(),
            "q_yn_rate":  g["is_ynq"].mean(),
        })
        for k in cols_dm:
            out[f"dm_{k}_per100utt"] = per100(int(g[f"dm_{k}_count"].sum()), n_utt)
        out["ms_total_per100w"] = per100(int(g["ms_total"].sum()), n_tok)
        dy_rows.append(out)
    dy = pd.DataFrame(dy_rows)

    # join to groups
    dj = dy.merge(dyads[[join_d, group_col]], left_on=join_u, right_on=join_d, how="left")
    dj["group_norm"] = dj[group_col].apply(normalize_group)
    grp = dj.groupby("group_norm")

    metrics = ["q_all_rate","q_wh_rate","q_yn_rate",
               "dm_fill_per100utt","dm_contrast_per100utt","dm_causal_per100utt","dm_shift_per100utt",
               "ms_total_per100w"]
    rows = []
    for gname, gg in grp:
        if gname not in ("ASD","TYP"):  # ignore others
            continue
        out = {"group": gname, "n_dyads": int(gg[join_u].nunique())}
        for m in metrics:
            out[m] = float(gg[m].mean())
        rows.append(out)
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).set_index("group").sort_index()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in_csv", required=True, help="utterances.csv")
    ap.add_argument("--out_csv", required=True, help="speaker summary out path")
    ap.add_argument("--dyads", default="", help="dyads.csv with group labels")
    ap.add_argument("--group_out_csv", default="", help="child ASD/TYP summary out path")
    ap.add_argument("--utter_key", default="", help="join key in utterances (e.g., dyad_id/child_uid/file)")
    ap.add_argument("--dyads_key", default="", help="join key in dyads (e.g., dyad_id/child_uid/file)")
    ap.add_argument("--group_col", default="diagnostic_group", help="group column in dyads (default: diagnostic_group)")
    args = ap.parse_args()

    # read utterances
    df = pd.read_csv(args.in_csv)
    df["speaker"] = df["speaker"].astype(str)
    txt = pick_text_col(df)
    df = add_per_utt_flags(df, txt)

    # (A) speaker summary (legacy)
    spk = speaker_summary(df)
    spk.to_csv(args.out_csv, index=True)
    print(f"[A] Wrote speaker summary: {args.out_csv}  shape={spk.shape}")

    # (B) child (CHI) group summary
    if not args.group_out_csv:
        print("[B] Skipped child group summary (no --group_out_csv given)")
        return

    chi = df[df["speaker"]=="CHI"].copy()
    if chi.empty:
        print("[B] Skipped child group summary (no CHI rows)")
        return

    # read dyads
    if not args.dyads:
        print("[B] Skipped child group summary (no --dyads given)")
        return
    try:
        dyads = pd.read_csv(args.dyads)
    except Exception as e:
        print(f"[B] Skipped child group summary (failed to read dyads: {e})")
        return

    # decide join keys
    prefer = (args.utter_key, args.dyads_key) if (args.utter_key and args.dyads_key) else None
    join_u, join_d, how = detect_join_keys(set(chi.columns), set(dyads.columns), prefer=prefer)

    if not join_u or not join_d:
        print(f"[B] Skipped child group summary (no common join key). "
              f"Utter cols={list(chi.columns)[:20]}..., Dyads cols={list(dyads.columns)[:20]}...")
        return

    if args.group_col not in dyads.columns:
        # try common fallbacks
        for cand in ["group","grp","dx","diagnosis","diag_group","ASD_TD"]:
            if cand in dyads.columns:
                args.group_col = cand
                break
    if args.group_col not in dyads.columns:
        print(f"[B] Skipped child group summary (group column '{args.group_col}' not found in dyads). "
              f"Available={list(dyads.columns)[:20]}...")
        return

    grp = child_group_summary(chi, dyads, join_u, join_d, args.group_col)
    if len(grp) > 0:
        grp.to_csv(args.group_out_csv, index=True)
        print(f"[B] Wrote child group summary: {args.group_out_csv}  shape={grp.shape}  "
              f"(join: utter.{join_u} ↔ dyads.{join_d} via {how}, group_col={args.group_col})")
    else:
        print("[B] Skipped child group summary (after join/grouping no ASD/TYP rows)")
if __name__ == "__main__":
    main()
