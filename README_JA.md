# Bang & Nadig (2015) 英語データ再現パック（Nadig, 9分窓・MOT/CHI分離）

## 目的
- **再現性（reproducibility）** と **説明可能性（interpretability）** を最優先に、Bang & Nadig (2015) 英語データ（TalkBank / ASDBank: Nadig）の主要指標を**決定的（deterministic）に再現**します。
- 親の入力（tokens/types/#utts/MLU）と **子の語彙多様性（NDW）** を分離し、**論文本値に準拠**しつつ、**9分の @Bg〜@Eg 区間**で子のNDWを厳密に再計算します。
- **年齢（T2_age_months）** もExcelから取り込み、ダッシュボードの「Paper vs Ours — Table 1」空欄を解消しました。

---

## 公開ダッシュボード（先生向けプレビュー）
- **https://leadlea.github.io/asd/bn2015_dashboard.html**

フッターに **生成時刻・使用ファイルの md5（Dyads/Desc/T-test）** を自動表示（Provenance）。

---

## 本パイプラインの設計思想（要点）

- **親の入力**（母親ティアを含む定義差の影響を排除）  
  → TalkBank配布の **公式Excel**（`bang_nadig.xlsx` の `language_matched_CHILDEScorpus`）にある **Parent_Token / Parent_Types / Parent_NumUtt / Parent_MLU** をそのまま採用。  
  併せて **Child_Age_Months → T2_age_months** を取り込み。

- **子（CHI）NDW**  
  → 各 `.cha` の **@Bg〜@Eg**（約9分）を抽出、**`*CHI:` のみ**を対象。  
  → **フィラー/相づち**は語彙から除外（`uh, um, hmm, mm, mhm, uhhuh, ah, oh, eh, er, erm, oof, oops, ...`）  
  → **縮約は分割しない**（NDWは `don't` を1語扱い。MLUは分割）。

- **マージキー**  
  → `dyads.9min.ndw_strict.patched.csv` を **num（3桁）↔ dyad_id** の対応表として信頼ソースに。  
  → 親/子の指標を **左外部結合**で `dyads.csv` にクリーン上書き。

- **先祖返り防止**  
  ダッシュボードは `out/bn2015/table3_descriptives_en.csv` / `table2_en_ttests.csv` を “ours” として参照するため、**ビルド直前に必ず dyads から再生成**します。

---

## 必要ファイル
```
Nadig/*.cha                         # TalkBank配布の英語トランスクリプト（@Bg/@Egを含む）
bang_nadig.xlsx                     # 公式Excel（language_matched_CHILDEScorpus）
dyads.csv                           # 既存ダイアド表（diagnostic_group, dyad_id 等）
dyads.9min.ndw_strict.patched.csv   # num↔dyad_id の対応（信頼マップ）
```

---

## 実行手順（コピペで再現可能）

> 乱数・並列非依存。**決定的**に同一結果が得られます。

### 1) 親入力を Excel から抽出（年齢付き）
```bash
python ./extract_parent_from_excel.with_age_robust.py   --xlsx bang_nadig.xlsx   --out  out/bn2015/parent9.csv
# 出力列例: num,input_word_tokens,input_word_types,input_num_utterances,input_mlu,T2_age_months
```

### 2) 子（CHI）NDW を 9分窓で再計算（フィラー除外）
```bash
python ./strict_9min_child_ndw.from_gems.stoplist.py   --chat_dir Nadig   --out out/bn2015/child9.csv
```

### 3) クリーンに統合（年齢も通す）
```bash
python ./force_merge_using_patched_map.py   --dyads dyads.csv   --parent out/bn2015/parent9.csv   --child  out/bn2015/child9.csv   --map    dyads.9min.ndw_strict.patched.csv   --out    dyads.9min.ndw_strict.csv

# 期待される群平均（例）:
# Tokens: ASD≈664.64 / TYP≈606.09
# MLU:    ASD≈5.06   / TYP≈5.66
# NDW:    ASD≈69.09  / TYP≈75.00
# Age:    ASD≈61.89  / TYP≈32.30
```

### 4) 記述統計・t検定を **今の dyads から再生成**（必須）
```bash
python ./make_en_desc_ttests_from_dyads.py   --dyads dyads.9min.ndw_strict.csv   --outdir out/bn2015
```

### 5) ダッシュボード生成（出所の明記付き）
```bash
python ./make_dashboard_with_provenance.py   --dyads dyads.9min.ndw_strict.csv   --desc  out/bn2015/table3_descriptives_en.csv   --ttest out/bn2015/table2_en_ttests.csv   --out   docs/bn2015_dashboard.html   --orig  ./make_dashboard.py
```

---

## NDW の除外ルール（再掲）
- 語彙に数えない：`uh, um, hmm, mm, mhm, uhhuh, ah, oh, eh, er, erm, oof, oops, ...`  
- 管理：`strict_9min_child_ndw.from_gems.stoplist.py` の `STOP` セットで制御。  
- 対象：**CHI**の 9分発話のみ。

---

## “Paper vs Ours” の見方
- **paper_mean / paper_sd**：Bang & Nadig (2015) の論文本体テーブル値。  
- **mine_mean / mine_sd**：本パイプラインで算出した値（親はExcel準拠、子NDWは9分再計算）。  
- したがって Table 2 の一部（例：TYP Tokens）は **paper と ours が意図的に異なる**場合があります（親をExcelに統一するため）。

---

## 既知の限界と今後
- 親入力の完全自動再算出（CLAN + MOR で母親ティアを解析）も将来対応可能。現状は**論文本値のExcel準拠**を優先。  
- フィラー辞書は監査ログに基づき拡張可能。  
- 他コーパス／日本語データへの水平展開は @Bg/@Eg とティア設計に依存。

---

## スクリプト一覧（本リポ）
- `extract_parent_from_excel.with_age_robust.py` …… 公式Excel → 親入力CSV（T2_age_months含む）  
- `strict_9min_child_ndw.from_gems.stoplist.py` …… Gems 9分×CHI → NDW（フィラー除外）  
- `force_merge_using_patched_map.py` …… num↔dyad マップで統合（年齢も通す）  
- `make_en_desc_ttests_from_dyads.py` …… **最新 dyads** から desc/ttest を再生成（先祖返り防止）  
- `make_dashboard_with_provenance.py` …… ダッシュボード生成＋Provenance追記

---

## 検証ログ例（あなたの実行）
```
ASD=11 / TYP=11

TYP input_word_tokens → 606.09 (sd 220.99)
ASD input_word_tokens → 664.64 (sd 222.29)
TYP input_mlu         → 5.66   (sd 0.74)
ASD input_mlu         → 5.06   (sd 0.92)
TYP T2_child_word_types → 75.00
ASD T2_child_word_types → 69.09
TYP T2_age_months       → 32.30
ASD T2_age_months       → 61.89
```
（ダッシュボードのフッター md5 が一致すれば、反映完了の合図です）

---

## 連絡先・ライセンス
- データ：TalkBank / ASDBank Nadig（配布条件に従う）  
- 研究：Bang & Nadig (2015) の成果物（Excel・メタ表）に深謝します。  
- 問い合わせ：Issue/Pull Request にて。改善提案歓迎。
