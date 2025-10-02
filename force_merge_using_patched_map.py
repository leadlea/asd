#!/usr/bin/env python3
import pandas as pd, argparse, re

def coerce_num_col(df, col='num'):
    df = df.copy()
    if col in df.columns:
        s = df[col].astype(str).str.extract(r'(\d{3})')[0]
        if s.notna().any():
            df[col] = s.astype('Int64')
    return df

ap = argparse.ArgumentParser()
ap.add_argument('--dyads',  required=True)
ap.add_argument('--parent', required=True)
ap.add_argument('--child',  required=True)
ap.add_argument('--map',    required=True)  # dyads.9min.ndw_strict.patched.csv
ap.add_argument('--out',    required=True)
a = ap.parse_args()

# 読み込み
d = pd.read_csv(a.dyads)
p = pd.read_csv(a.parent)
c = pd.read_csv(a.child)
m = pd.read_csv(a.map)

# numの正規化
p = coerce_num_col(p, 'num')
c = coerce_num_col(c, 'num')
m = coerce_num_col(m, 'num')

# mapに必須列があるか確認
if not {'dyad_id','num'}.issubset(set(m.columns)):
    raise SystemExit("map(csv)に 'dyad_id' と 'num' が必要です: " + a.map)

# 親/子に dyad_id を付与
p2 = p.merge(m[['num','dyad_id']].drop_duplicates(), on='num', how='left')
c2 = c.merge(m[['num','dyad_id']].drop_duplicates(), on='num', how='left')

# dyads 側をクリーンにしてから左外部結合
drop_cols = [col for col in d.columns
             if col.startswith('input_') or col.startswith('child9_') or col=='T2_child_word_types']
base_cols = [col for col in d.columns if col not in drop_cols]
out = d[base_cols].copy()

# ★ 既存に T2_age_months があれば一旦落として、親の列で上書きする
if 'T2_age_months' in out.columns and 'T2_age_months' in p2.columns:
    out = out.drop(columns=['T2_age_months'])

# ★ 親から通す列に T2_age_months を追加
need_p = [x for x in [
    'dyad_id','input_word_tokens','input_word_types','input_num_utterances','input_mlu','T2_age_months'
] if x in p2.columns]
need_c = [x for x in [
    'dyad_id','child9_ndw_strict','child9_tokens_strict','child9_utts_strict'
] if x in c2.columns]

out = out.merge(p2[need_p], on='dyad_id', how='left')
out = out.merge(c2[need_c], on='dyad_id', how='left')

# 子NDW → T2_child_word_types
if 'child9_ndw_strict' in out.columns:
    out['T2_child_word_types'] = pd.to_numeric(out['child9_ndw_strict'], errors='coerce')

# 数値化
for col in ['input_word_tokens','input_word_types','input_num_utterances','input_mlu','T2_age_months']:
    if col in out.columns:
        out[col] = pd.to_numeric(out[col], errors='coerce')

out.to_csv(a.out, index=False)
print("[INFO] wrote:", a.out, "rows:", len(out))
if 'diagnostic_group' in out.columns:
    for col in ['input_word_tokens','input_mlu','T2_child_word_types','T2_age_months']:
        if col in out.columns:
            print("\n[SUMMARY]", col)
            print(out.groupby('diagnostic_group')[col].mean())
