#!/usr/bin/env python3
import argparse, pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument('--dyads', required=True)
ap.add_argument('--xlsx',  required=True)
ap.add_argument('--sheet', default='language_matched_CHILDEScorpus')
# 既存運用に合わせて許容率を設定
ap.add_argument('--tol_tokens_typ', type=float, default=0.25)
ap.add_argument('--tol_tokens_asd', type=float, default=0.35)
ap.add_argument('--tol_mlu',        type=float, default=0.25)
ap.add_argument('--tol_child',      type=float, default=0.40)  # TYP
ap.add_argument('--tol_child_asd',  type=float, default=0.45)  # ASD
a = ap.parse_args()

dy = pd.read_csv(a.dyads)
ex = pd.read_excel(a.xlsx, sheet_name=a.sheet)
ex = ex[ex['Language'].astype(str).str.contains('English', case=False, na=False)].copy()

# Excel -> ターゲット算出
ex_targets = {
    ('TYP','input_word_tokens'): (ex[ex['Group'].str.upper()=='TYP']['Parent_Token'].mean(), ex[ex['Group'].str.upper()=='TYP']['Parent_Token'].std()),
    ('ASD','input_word_tokens'): (ex[ex['Group'].str.upper()=='ASD']['Parent_Token'].mean(), ex[ex['Group'].str.upper()=='ASD']['Parent_Token'].std()),
    ('TYP','input_mlu')        : (ex[ex['Group'].str.upper()=='TYP']['Parent_MLU'].mean(),   ex[ex['Group'].str.upper()=='TYP']['Parent_MLU'].std()),
    ('ASD','input_mlu')        : (ex[ex['Group'].str.upper()=='ASD']['Parent_MLU'].mean(),   ex[ex['Group'].str.upper()=='ASD']['Parent_MLU'].std()),
    ('TYP','T2_child_word_types'):(ex[ex['Group'].str.upper()=='TYP']['Child_Types'].mean(), ex[ex['Group'].str.upper()=='TYP']['Child_Types'].std()),
    ('ASD','T2_child_word_types'):(ex[ex['Group'].str.upper()=='ASD']['Child_Types'].mean(), ex[ex['Group'].str.upper()=='ASD']['Child_Types'].std()),
}

print("n by group:\n", dy['diagnostic_group'].value_counts(dropna=False), "\n")

def check(grp, col, tol):
    target_mean, target_sd = ex_targets[(grp,col)]
    sub = dy[dy['diagnostic_group']==grp]
    obs_m = sub[col].mean()
    obs_s = sub[col].std(ddof=1)
    ok = abs(obs_m - target_mean) <= tol * target_mean if pd.notna(obs_m) else False
    status = "PASS" if ok else "FLAG"
    print(f"{grp:3s} {col:22s} -> {status} | obs mean={obs_m:.2f}, sd={obs_s:.2f} | target mean={target_mean:.2f}, sd={target_sd:.2f} (±{int(tol*100)}%)")

check('TYP','input_word_tokens', a.tol_tokens_typ)
check('ASD','input_word_tokens', a.tol_tokens_asd)
check('TYP','input_mlu',        a.tol_mlu)
check('ASD','input_mlu',        a.tol_mlu)
check('TYP','T2_child_word_types', a.tol_child)
check('ASD','T2_child_word_types', a.tol_child_asd)

zeros = (dy['T2_child_word_types'].fillna(0) == 0).sum()
print(f"\nZero T2_child_word_types rows: {zeros}")
