#!/usr/bin/env python3
import argparse, pathlib as P, re, pandas as pd

WORD = re.compile(r"[A-Za-z]+")
# よく出るフィラー・相づち（必要なら後で追加可）
STOP = {
    "uh","um","huh","eh","er","erm","mmm","mm","hmm","mhm","uhhuh","uhuh","ah","oh","oops","oof","huhhuh",
    "uhm","umm","mmhm","hmmm","huh?","uh-huh"  # 生起に備えて素の形も
}

def tok_for_ndw(s: str):
    # 注記・特殊記号除去（CHAT準拠の軽処理）
    s = re.sub(r'\[[^\]]*\]', ' ', s)          # [注記] を落とす
    s = re.sub(r'&[-a-z]+', ' ', s)            # &xxx 系を落とす
    s = s.lower()
    s = re.sub(r'-', '', s)                    # uh-huh → uhhuh（STOPで一括除外）
    s = re.sub(r'[()<>{}~^@#*\\/"“”‘’`]', ' ', s)
    toks = WORD.findall(s)                     # 縮約は分割しない（don'tは1語）
    # フィラー除外
    toks = [w for w in toks if w not in STOP]
    return toks

def num_from(path: P.Path):
    m = re.search(r'(\d{3})', path.name); return int(m.group(1)) if m else None

def find_bg_eg(lines):
    bg = next((i for i,l in enumerate(lines) if l.lstrip().lower().startswith('@bg')), None)
    eg = next((i for i,l in enumerate(lines) if l.lstrip().lower().startswith('@eg')), None)
    return bg, eg

def chi_metrics(lines, lo:int, hi:int):
    types=set(); toks=0; utts=0
    for i in range(lo, hi+1):
        ln = lines[i]
        if not ln.startswith('*CHI:'): continue
        cut = ln.split('\x15',1)[0]
        if cut.startswith('*CHI:'): cut = cut[5:]
        ws = tok_for_ndw(cut)
        utts += 1; toks += len(ws); types.update(ws)
    return len(types), toks, utts

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chat_dir', required=True)  # Nadig
    ap.add_argument('--out',      required=True)  # out/bn2015/child9.csv
    a = ap.parse_args()

    rows=[]
    for cha in sorted(P.Path(a.chat_dir).glob('*.cha')):
        num = num_from(cha)
        if num is None: continue
        lines = cha.read_text(encoding='utf-8', errors='ignore').splitlines()
        bg, eg = find_bg_eg(lines)
        if bg is None or eg is None or eg <= bg:
            rows.append({'num':num,'child9_ndw_strict':0,'child9_tokens_strict':0,'child9_utts_strict':0}); continue
        ndw, toks, utts = chi_metrics(lines, bg, eg)
        rows.append({'num':num,'child9_ndw_strict':ndw,'child9_tokens_strict':toks,'child9_utts_strict':utts})

    pd.DataFrame(rows).sort_values('num').to_csv(a.out, index=False)
    print("Wrote", a.out, "rows:", len(rows))

if __name__=='__main__':
    main()
