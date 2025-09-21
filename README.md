# ASD Pragmatics MVP (EN) — README

本リポジトリは、公開英語コーパス **ASDBank** と **CHILDES/TalkBank** を用いて、ASD（自閉スペクトラム症）とTD（定型発達）の**語用論的な違い**を「まず動く形」で検証する **MVP**（最小実装）です。

- **モダリティ**：本MVPは **CHAT（`.cha`）テキスト**からの指標化のみを行います。**実音声（`.wav`）は使用していません。**
- 本READMEやレポートで言及する **「音声／プロソディ」** は、`.cha` 上の**フィラー（um, uh）・ポーズ記号 (.)・反復の記法**などから導く **「テキスト由来の代理指標」** を意味します（実音響特徴ではありません）。

**公開レポート（GitHub Pages）**：https://leadlea.github.io/asd/ASD_TD_MVP_Report.html

---

## 現在地（2025-09-22 JST）

- **取り込み & QC**：英語 ASD/TD の会話記録（`.cha`）を収集し、IQR/Percentile に基づく自動しきい値で**セッション品質チェック**を実施。
- **特徴量（抜粋）**：
  - **談話標識**（例: well, you know）頻度
  - **不流暢**（um/uh、反復記号などテキスト上の表示）
  - **代名詞**（1–3人称）
  - **心的状態語**（think, know, want 等の軽量辞書）
  - **参照表現**（導入/維持/再導入/曖昧の近似ラベル：noun_chunks＋固有表記の簡易扱い）
  - **トピック粘着度**（直前発話との内容語レンマ重なり）
  - ※ **「音声系」= テキスト代理指標**（実音声特徴は未使用）
- **評価（LoCO: paired, calibrated）**：主指標は **AUC_adj**（閾値に依存しない分離力）。表の **F1_cal** は **「学習側CVで得た各 fold の最適閾値」**での**参考値**（運用の固定閾値とは別）です。
- **意思決定の方針**：運用・比較の簡素化のため、**CV スイープで得た最初の最適点 0.55 を MVP の固定しきい値**として採用。以後の再評価は **AUC 中心＋固定0.55下の混同行列/F1**で示します。
- **NLP基盤**：spaCy `en_core_web_sm` を**語用論指標の算出に限定して**使用（文分割・品詞・noun_chunks・軽量NER）。
- **成果物**：`docs/ASD_TD_MVP_Report.html` にサマリー、指標、LoCO比較、図表を集約。

---

## 評価ポリシー（誤解防止のための明記）

1. **主指標は AUC（および AUC_adj）**  
   - しきい値に依存しない分離力を比較するため、まず AUC を見ます。
2. **固定しきい値 0.55（運用仮置き）**  
   - **2025-09-19** の **threshold sweep（CV確率）**で **F1 最大化**により得た**最初の最適点 0.55** を、MVPの**固定閾値**として採用。以降は **再現性・比較性**を優先して 0.55 を用います。
3. **F1_cal の位置づけ**  
   - レポートに出てくる **F1_cal** は、**fold 内の学習側CVから得た最適閾値**による**参考値**です。**運用レベルの固定値（0.55）とは別**であることを明記します。
4. **キャリブレーション**  
   - Platt/Isotonic などの確率校正は**比較目的の検証**として実施。**主結果は AUC 中心**で解釈します。

---

## Quickstart（再現手順の最小セット）

> 依存は `requirements.txt` を参照。乱数は `SEED` を固定。

```bash
# 1) 環境準備
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2) データ配置
#   raw/ に .cha を配置（音声 .wav は不要）
#   meta/ にメタデータ（年齢, MLU, グループ等）
tree data/

# 3) 取り込み → 語用論特徴 → マージ
python -m src.ingest.chat_to_csv   --in_dir data/raw_mvp   --out_csv data/interim/utterances.csv

python -m src.features.pragmatics   --in_csv data/interim/utterances.csv   --out_csv data/interim/pragmatics_features.csv

python -m src.pipeline.run_all   --prag_csv data/interim/pragmatics_features.csv   --pros_csv data/interim/prosody_features.csv   --meta_csv data/interim/metadata.csv   --out_csv data/processed/features_merged.csv
# 注：prosody_features.csv はテキスト代理指標。実音声は未使用。

# 4) ベースライン学習（固定閾値0.55は評価側で適用）
python -m src.models.baseline   --feat_csv data/processed/features_merged.csv   --report_json reports/baseline_report.json

# 5) LoCO（paired+calibrated）
python -m scripts.loco_eval_plusref_meta   --feat_csv data/processed/features_merged.csv   --out_csv reports/loco_results_paired_calibrated.csv

# 6) 図表とレポート（docs/ に出力）
python -m scripts.make_report   --loco_csv reports/loco_results_paired_calibrated.csv   --out_html docs/ASD_TD_MVP_Report.html
```

- **評価時の固定閾値適用**：
  - 0.55 を明示的に指定する評価スクリプト（例：`--threshold 0.55`）を用意。
  - 別途、**F1_cal** を算出する場合は「**fold内CVの最適閾値**」を使い、**固定0.55とは混同しない**ように結果欄を分けて記載。

---

## データソース / 仕様（厳密な用語の扱い）

- **コーパス**：ASDBank（臨床）、CHILDES（小児言語）ほか英語会話データ。
- **形式**：CHAT / CLAN（`.cha`）。
- **モダリティ**：**`.cha`テキストのみ**。**`.wav` など実音声は未使用**。
- **「音声」表記**：テキスト上の **フィラー・ポーズ記号・反復**に基づく **プロソディの代理指標**を指す。
- **NLP基盤**：spaCy `en_core_web_sm`（文分割・品詞・noun_chunks・軽量NER）。**語用論指標算出に限定利用**。
- **特徴量の層別**：年齢・MLU・コーパス差を**レポート側で可視化**（因果の断定は避ける）。
- **倫理・配布**：元データの**再配布不可**。研究目的の引用・要約のみ。

---

## 既知の制約と今後

- **参照表現の精緻化**：固有表記辞書・照応の厳密化は**次フェーズ**で強化予定。
- **実音声特徴**：話速・韻律等の音響指標は**未使用**（今後、Praat/opensmile 等で拡張可）。
- **運用閾値の設計**：MVPでは **0.55固定**。次段では **感度優先/PPV優先**など**ポリシー別**に再設計し、必要なら**一括キャリブレーション**で尺度を統一。

---

## ライセンス / 謝辞

- 本リポジトリのコードはプロジェクトライセンスに従います（詳細は `LICENSE` を参照）。
- データは各コーパスのライセンスに従い、**再配布しません**。
- 謝辞は、関係各位のご許可を頂いた段階で `docs/` に追記します。
