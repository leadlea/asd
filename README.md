# ASD Pragmatics MVP (EN) — Status & How-to

本リポジトリは、公開英語コーパス **ASDBank** と **CHILDES/TalkBank** を用いて  
ASD/TD の語用論指標（談話標識・不流暢・代名詞・心的状態語＋参照表現）を検証する **MVP** です。  
データは CHAT（`.cha`）形式に準拠します。

**公開レポート（GitHub Pages）**: https://leadlea.github.io/asd/

---

## ✅ 現在地（2025-09-21）
- **取り込み & QC**：英語 ASD/TD 全体を収集し、自動閾値（IQR/Percentile）でセッション QC 済み。
- **特徴**：DM／不流暢／代名詞1–3人称／心的状態語に加え、**参照表現（導入/維持/再導入/曖昧）**を実装。
- **LoCO（paired, calibrated）**：
  - Base → AUC_adj の中央値 ~0.62
  - **+Reference+Meta（MLU/CHI）** → 複数 fold で **AUC_adj 0.90+**（例: Rollins+Sachs 0.952 / F1 0.737）
- **アブレーション（5-fold, thr=0.55）**：寄与大＝**不流暢 per_utt > 談話標識 per_utt > 談話標識 per_1k > 不流暢 per_1k**  
- **成果物**：`docs/ASD_TD_MVP_Report.html` に図・表・KPI・LoCO 比較を集約。

---

## Quickstart

```bash
# 0) セットアップ
python -m pip install -U pip
pip install pandas numpy scikit-learn matplotlib "spacy<3.8"
python -m spacy download en_core_web_sm

# 1) 取り込み（.cha → 発話CSV）
python src/ingest/chat_to_csv.py --in_dir data/raw --out_csv data/interim/utterances.csv

# 2) クリーニング & QC（ASD/TD 別）
python qc_auto.py --utterances data/processed/utterances_clean_asd.csv   --out_csv data/processed/utterances_qc_asd.csv   --out_metrics reports/session_metrics_asd.csv   --out_speaker reports/speaker_metrics_asd.csv   --save_thresholds reports/qc_auto_thresholds_asd.json

python qc_auto.py --utterances data/processed/utterances_clean_td.csv   --out_csv data/processed/utterances_qc_td.csv   --out_metrics reports/session_metrics_td.csv   --out_speaker reports/speaker_metrics_td.csv   --save_thresholds reports/qc_auto_thresholds_td.json

# 3) 参照表現（子: CHI）
python scripts/refexpr_features.py --utter data/processed/utterances_qc_asd.csv --out reports/features_ref_asd.csv
python scripts/refexpr_features.py --utter data/processed/utterances_qc_td.csv  --out reports/features_ref_td.csv

# 4) 特徴結合（+Reference / +Meta）
python - <<'PY'
import pandas as pd, pathlib as P
B=P.Path("reports")
def join(a, r, out): pd.read_csv(B/a).merge(pd.read_csv(B/r),on="file_id",how="left").to_csv(B/out, index=False)
join("features_child_asd.csv","features_ref_asd.csv","features_child_asd_plusref.csv")
join("features_child_td.csv","features_ref_td.csv","features_child_td_plusref.csv")
asm=pd.read_csv(B/"session_metrics_asd.csv")[["file_id","chi_ratio","mlu_child","mlu_adult"]]
tsm=pd.read_csv(B/"session_metrics_td.csv")[["file_id","chi_ratio","mlu_child","mlu_adult"]]
pd.read_csv(B/"features_child_asd_plusref.csv").merge(asm,on="file_id",how="left").to_csv(B/"features_child_asd_plusref_meta.csv",index=False)
pd.read_csv(B/"features_child_td_plusref.csv").merge(tsm,on="file_id",how="left").to_csv(B/"features_child_td_plusref_meta.csv",index=False)
print("-> plusref_meta done")
PY

# 5) LoCO（paired+calibrated, 学習内F1最適閾値）
#   ※ スクリプト化した場合: scripts/loco_eval_plusref_meta.py
python - <<'PY'
import pandas as pd, numpy as np, re, itertools as it
from pathlib import Path
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score, f1_score
R=Path("reports")
a=pd.read_csv(R/"features_child_asd_plusref_meta.csv"); a["y"]=1
t=pd.read_csv(R/"features_child_td_plusref_meta.csv"); t["y"]=0
df=pd.concat([a,t], ignore_index=True)
def corpus(fid): import re; m=re.search(r"_(\w+)_\d+", str(fid)); return m.group(1) if m else "UNK"
df["corpus"]=df["file_id"].apply(corpus)
feats=[c for c in df.columns if c.endswith("_per_1k") or c.endswith("_per_utt") or c in ("chi_ratio","mlu_child","mlu_adult")]
def best_thr(X,y):
    from sklearn.model_selection import StratifiedKFold; from sklearn.metrics import f1_score, roc_auc_score
    sk=StratifiedKFold(n_splits=5, shuffle=True, random_state=42); ts=[]
    for tr,va in sk.split(X,y):
        from sklearn.pipeline import Pipeline; from sklearn.linear_model import LogisticRegression; from sklearn.preprocessing import StandardScaler
        pipe=Pipeline([("sc",StandardScaler()),("lr",LogisticRegression(max_iter=800,class_weight="balanced"))])
        pipe.fit(X[tr],y[tr]); p=pipe.predict_proba(X[va])[:,1]
        auc=roc_auc_score(y[va],p); 
        if auc<0.5: p=1-p
        import numpy as np
        qs=np.quantile(p,np.linspace(0.05,0.95,19))
        ts.append(qs[int(np.argmax([f1_score(y[va],(p>=q).astype(int)) for q in qs]))])
    import numpy as np
    return float(np.mean(ts)) if ts else 0.5
lab_by_c=df.groupby("corpus")["y"].mean().map(lambda p:"ASD" if p>0.5 else "TD")
asd_c=sorted([c for c,l in lab_by_c.items() if l=="ASD"]); td_c=sorted([c for c,l in lab_by_c.items() if l=="TD"])
rows=[]
for ac in asd_c:
  for tc in td_c:
    te=df[df["corpus"].isin([ac,tc])]; tr=df[~df["corpus"].isin([ac,tc])]
    Xtr,ytr=tr[feats].fillna(0).values, tr["y"].values
    Xte,yte=te[feats].fillna(0).values, te["y"].values
    if len(set(ytr))<2 or len(set(yte))<2:
        rows.append({"fold":f"{ac}+{tc}","AUC_adj":np.nan,"F1_cal":np.nan,"thr":np.nan,"note":"imbalance"}); continue
    thr=best_thr(Xtr,ytr)
    pipe=Pipeline([("sc",StandardScaler()),("lr",LogisticRegression(max_iter=800,class_weight="balanced"))]).fit(Xtr,ytr)
    p=pipe.predict_proba(Xte)[:,1]; auc=roc_auc_score(yte,p)
    if auc<0.5: p=1-p; auc=1-auc
    rows.append({"fold":f"{ac}+{tc}","AUC_adj":round(auc,3),"F1_cal":round(f1_score(yte,(p>=thr).astype(int)),3),"thr":round(thr,3)})
pd.DataFrame(rows).sort_values("fold").to_csv(R/"loco_results_paired_calibrated_plusref_meta.csv", index=False)
print("wrote ->", R/"loco_results_paired_calibrated_plusref_meta.csv")
PY

# 6) レポート更新（docs/ASD_TD_MVP_Report.html に追記）
#   ※ scripts/build_html_report.py で自動追記可能
```

---

## データソース / 仕様
- ASDBank（English: Nadig / Rollins / …）— TalkBank 臨床系。アクセスは登録制。  
- CHILDES（Eng-NA/Eng-UK ほか）— 子ども言語の主要リポジトリ。  
- CHAT/CLAN — `.cha` 仕様・ツール群。

---

## GitHub Pages（公開方法）
Settings → Pages → **Deploy from a branch**／**Branch: main**／**Folder: /docs**。  
`docs/index.html` から `ASD_TD_MVP_Report.html` にリダイレクト。

---

## 積み残しタスク（先生のご助言を反映）
### A. レビュー整理
- [ ] 語用論指標マップ（話題維持・ターンテイク・談話標識・比喩/含意・指示/参照・心的状態語）
- [ ] 各指標の実装ステータス表（実装済／近似／今後）→ 技術メモ（2p）で共有

### B. 英語MVPの最終仕上げ（今週）
- [ ] LoCO 先頭要約（平均 AUC_adj/F1_cal、Providence の難度メモ）
- [ ] 参照表現の精緻化（固有表記辞書・軽量コア参照近似）
- [ ] Providence 低下要因の分析（話題・年齢・収録条件）
- [ ] タグ `v0.2.0-en-mvp` を切る（再現プリセットと commit hash）
- [ ] 先生向け 1 枚スライド（KPI・上位特徴・LoCO）

### C. 日本語版（別ブランチ `feature/jp-mvp`）
- [ ] 英→日対訳＋**後編集ルール**（終助詞・談話標識）で語用論保持を検証
- [ ] 日本語側の参照表現近似（指示語／係り受け＋ゼロ代名詞簡易検出）
- [ ] 公開日本語コーパスが出たら LoCO を英日横断で再評価

### D. データ利用・倫理
- [ ] 当事者研究（熊谷先生）へのデータ利用許可申請の準備（要約／想定成果物）
- [ ] TalkBank/CHILDES/ASDBank の利用規約注記（データ再配布不可）を README に明記
