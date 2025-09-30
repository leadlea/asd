#!/usr/bin/env python3
import pandas as pd, argparse

ap = argparse.ArgumentParser()
ap.add_argument('--xlsx', required=True)   # bang_nadig.xlsx
ap.add_argument('--out',  required=True)   # out/bn2015/parent9.csv
ap.add_argument('--sheet', default='language_matched_CHILDEScorpus')
a = ap.parse_args()

df = pd.read_excel(a.xlsx, sheet_name=a.sheet)

# 英語のみ
df = df[df['Language'].astype(str).str.contains('English', case=False, na=False)].copy()

# 列を厳密に拾う（このシートのカラム名に合わせる）
need = {
    'Subject':'num',
    'Parent_Token':'input_word_tokens',
    'Parent_Types':'input_word_types',
    'Parent_NumUtt':'input_num_utterances',
    'Parent_MLU':'input_mlu',
}
missing = [k for k in need if k not in df.columns]
if missing:
    raise SystemExit(f"Excelに必要列がありません: {missing}")

out = df[list(need.keys())].rename(columns=need)
# 3桁num & 数値化
out['num'] = pd.to_numeric(out['num'], errors='coerce').astype('Int64')
for c in ['input_word_tokens','input_word_types','input_num_utterances','input_mlu']:
    out[c] = pd.to_numeric(out[c], errors='coerce')

# 重複排除・並べ替え
out = out.dropna(subset=['num']).drop_duplicates(subset=['num']).sort_values('num')
out.to_csv(a.out, index=False)
print("Wrote", a.out, "rows:", len(out))
