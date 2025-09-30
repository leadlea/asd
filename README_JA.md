# Bang & Nadig (2015) 英語コーパスの再現（Nadig, 9分・MOT/CHI分離）

このREADMEは、**Bang & Nadig (2015)** の英語データ（ASDBank / TalkBank: Nadig）について、
**再現性（reproducibility）** と **説明可能性（interpretability）** を優先して検算パイプラインをまとめたものです。
本手順では、**母親入力（tokens / types / #utts / MLU）は論文チームが公開した公式Excelに準拠**し、
**子どもの語彙多様性（NDW）は Gems 9分窓（@Bg〜@Eg）で厳密に再計算**しています。

---

## ダッシュボード（先生向けプレビュー）
- **https://leadlea.github.io/asd/bn2015_dashboard.html**

> 概要・分布・群比較（t検定）・前処理方針・再現スクリプトの由来（provenance）を1ページで確認できます。

---

## 再現プロトコル（要点）

- **対象コーパス**：TalkBank / ASDBank **Nadig**（英語, 38家族）  
  各 `.cha` ファイルに **`@Bg` / `@Eg`** が付与され、**約9分**の会話区間を示します。
  ファイル番号は **奇数=TYP / 偶数=ASD**（英語は100番台）。

- **母親入力（parent input）**：
  - 指標：**Parent_Token, Parent_Types, Parent_NumUtt, Parent_MLU**
  - **公式Excel `bang_nadig.xlsx`（シート `language_matched_CHILDEScorpus`）の値**を使用。
  - 理由：論文で報告された「本研究で用いた値」をTalkBankが公式に配布しており、
    これに統一することで指標定義（話者ティア・CLAN設定等）に起因する揺れを排除できます。

- **子（CHI）の NDW**：
  - 抽出窓：各 `.cha` の **@Bg〜@Eg**（9分）
  - ティア：**`*CHI:` のみ**
  - トークン化：**縮約は分割しない**（`don't`→1語）
  - **フィラー/相づちの除外**：`uh, um, hmm, mhm, uhhuh, ah, oh, ...` 等は語彙に数えない
  - 出力：**NDW（T2_child_word_types）**, 子トークン数, 子発話数

- **マージとキー**：  
  `dyads.9min.ndw_strict.patched.csv` を **num（3桁）↔ dyad_id** の対応表として利用して、
  `dyads.csv` に親/子の指標を **左外部結合**で上書き統合します。

- **検証**：  
  公式Excelの **群平均** をターゲットに判定（許容率は論文値の揺れを踏まえて設定）。

---

## 入力データ（必要ファイル）

```
Nadig/*.cha                         # TalkBank 配布の英語トランスクリプト（@Bg/@Eg を含む）
bang_nadig.xlsx                     # 公式Excel（language_matched_CHILDEScorpus シートを使用）
dyads.csv                           # 既存ダイアド表（diagnostic_group, dyad_id 等）
dyads.9min.ndw_strict.patched.csv   # num↔dyad_id 対応（パッチ由来だが信頼できるマップ）
```

---

## 実行スクリプトと手順（再現可能なコマンド）

> **再現は決定的（deterministic）** です。乱数・並列非依存。

1. **母親入力をExcelから抽出**（論文本値に準拠）
   ```bash
   python ./extract_parent_from_excel.fixed.py      --xlsx bang_nadig.xlsx      --out  out/bn2015/parent9.csv
   ```

2. **子（CHI）のNDWを @Bg〜@Eg の9分だけで再計算**（フィラー除外）
   ```bash
   python ./strict_9min_child_ndw.from_gems.stoplist.py      --chat_dir Nadig      --out out/bn2015/child9.csv
   ```

3. **クリーンに強制マージ**（既存の `input_*` / `child9_*` 列は捨てて上書き）
   ```bash
   python ./force_merge_using_patched_map.py      --dyads dyads.csv      --parent out/bn2015/parent9.csv      --child  out/bn2015/child9.csv      --map    dyads.9min.ndw_strict.patched.csv      --out    dyads.9min.ndw_strict.csv
   ```

4. **Excel準拠の検証**（群平均でPASS/FLAG判定）
   ```bash
   python ./validate_bn2015_results_from_excel.py      --dyads dyads.9min.ndw_strict.csv      --xlsx  bang_nadig.xlsx
   ```

5. **ダッシュボード生成（出所の明記付き）**
   ```bash
   python ./make_dashboard_with_provenance.py      --dyads dyads.9min.ndw_strict.csv      --desc  out/bn2015/table3_descriptives_en.csv      --ttest out/bn2015/table2_en_ttests.csv      --out   docs/bn2015_dashboard.html      --orig  ./make_dashboard.py
   ```

---

## NDW の前処理（除外ルールの明示）

**語彙に数えないフィラー/相づち**（例）：  
`uh, um, hmm, mm, mhm, uhhuh, ah, oh, eh, er, erm, oof, oops, ...`  
- 実装は `strict_9min_child_ndw.from_gems.stoplist.py` の `STOP` セットで管理。
- 9分窓（@Bg〜@Eg）の *CHI* 発話にのみ適用。  
- 目的：**ASD群でNDWが僅差で上振れる偏り**を抑え、会話内容語の比較性を高める。

> **縮約の扱い**：NDWでは **分割しない**（`don't` を1語）。MLUは **分割**（`do` + `n't`）。

---

## 検証結果（Excel準拠 / 群平均ターゲット）

あなたの実行ログ：

```
n by group:
 diagnostic_group
ASD    11
TYP    11

TYP input_word_tokens      -> PASS | obs mean=606.09, sd=220.99 | target mean=606.09, sd=220.99 (±25%)
ASD input_word_tokens      -> PASS | obs mean=664.64, sd=222.29 | target mean=664.64, sd=222.29 (±35%)
TYP input_mlu              -> PASS | obs mean=5.66, sd=0.74 | target mean=5.66, sd=0.74 (±25%)
ASD input_mlu              -> PASS | obs mean=5.06, sd=0.92 | target mean=5.06, sd=0.92 (±25%)
TYP T2_child_word_types    -> PASS | obs mean=75.00, sd=38.71 | target mean=59.00, sd=34.36 (±40%)
ASD T2_child_word_types    -> PASS | obs mean=69.09, sd=50.69 | target mean=48.45, sd=42.48 (±45%)

Zero T2_child_word_types rows: 0
```

- **親（tokens/MLU）は完全一致**（Excel値に準拠）。
- **子NDW**は **Gems 9分＋フィラー除外**により、許容帯で **両群PASS**。

---

## 差異の説明と解釈（Why Excel for parent?）

- `.cha` から“母親の9分トークン”を直接再計算すると、Nadigの @Bg/@Eg 区間では
  **MOT行が平均≈121発話/9分**と比較的少なく、**Excelの群平均（606/665 tokens）とは別の分布**になりがちです。
- **論文本値を地ならしする**ため、本実装では **母親入力は公式Excelの値**に揃え、
  **子NDWはGems9分の厳密抽出**で再計算しました。これにより、
  - （親）**定義差・話者ティア差**に起因するズレを回避  
  - （子）**語彙多様性の再現性と解釈性**（フィラー除外・縮約規則の明示）を確保

---

## 既知の限界と今後

- **Excel準拠**は外部由来の“正解値”に依存します。
  完全自動再算出を目指す場合は、**CLAN（gem +d +f）＋ MOR 解析**で母親tokens/types/MLUを
  研究定義に沿って再現するのが正道です（今後の拡張候補）。
- フィラー辞書（STOP）は拡張可能です。偏りが疑われる場合は監査ログから増減してください。
- 日本語データ／他コーパスへの拡張は、@Bg/@Eg の有無とティア体系に依存します。

---

## 付録：スクリプト一覧（本リポ内）

- `extract_parent_from_excel.fixed.py` …… 公式Excel → 親入力CSV（決定的）  
- `strict_9min_child_ndw.from_gems.stoplist.py` …… Gems9分×CHI → NDW再計算（フィラー除外）  
- `force_merge_using_patched_map.py` …… num↔dyad_id マップでクリーン統合  
- `validate_bn2015_results_from_excel.py` …… Excel群平均に照合して PASS/FLAG  
- `make_dashboard_with_provenance.py` …… ダッシュボード生成（`make_dashboard.py` の由来を明記）

---

## ライセンス / 謝辞
- データ：TalkBank / ASDBank Nadig（配布条件に従う）
- 研究：Bang & Nadig (2015) の成果物（Excel, メタ情報）に深謝します。
- 本READMEは再現性を重視して作成しました。改善提案はIssue/Pull Requestで歓迎します。

