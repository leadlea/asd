# 談話（会話テキスト）から LLM/PLM で ASD 特性・指標を推定する先行研究サーベイ（国内・海外）
Last updated: 2026-02-27 (JST)  
Owner: 福原玄（draft for GitHub sharing）  
Scope: **談話/会話テキスト（書き起こし・自由記述・口頭自由回答の転記）** → **LLM/PLM** → **ASD関連の指標（分類/回帰/症状項目）**

---

## 1. エグゼクティブサマリー（要点）
- **「談話 × LLM/PLM × ASD」**の研究は 2024〜2026 で増えているが、主流は  
  - **(A) ASD/TD の二値分類**（小規模・非公開データが多い）  
  - **(B) ADOS の特定項目（例：A4）など“限定ターゲット”の推定**  
  - **(C) 重症度（連続値）回帰**（主に PLM + ASR/転記、言語は英語/韓国語が中心）
- 一方で、**AQ/SRS 等の“多次元 traits（連続プロファイル）”を談話から直接推定し、再現可能に比較評価**した形は、少なくとも本調査範囲では明確な定番ベンチマークとして確立していない（＝ギャップになり得る）。

---

## 2. 調査方針（検索戦略と選定基準）
### 2.1 検索チャネル
- 医学・心理: PubMed
- 計算言語: ACL Anthology / LREC-COLING / Interspeech 周辺
- プレプリント: arXiv / OpenReview
- 国内: 学会公開PDF（例：SICE支部研究会資料）

### 2.2 代表的検索クエリ（概念組合せ）
- (autism OR ASD OR “autistic traits” OR ADOS OR SRS OR AQ)  
  AND (dialogue OR conversation OR discourse OR transcript OR “open-ended”)  
  AND (LLM OR “large language model” OR GPT OR ChatGPT OR BERT OR RoBERTa)
- 日本語: (自閉スペクトラム OR ASD) AND (会話 OR 談話 OR 書き起こし OR 自由記述) AND (大規模言語モデル OR BERT OR GPT)

### 2.3 インクルージョン/エクスクルージョン
**Include**
- 入力が「会話/談話テキスト」（面接転記、自由記述、口頭自由回答の書き起こし等）
- 出力がASD関連（分類 or 症状項目 or 重症度/スコア回帰）
- LLM/PLM の利用が明確（BERT/RoBERTa を含める）

**Exclude**
- LLMが“支援チャット”用途のみで、推定タスクが主目的でない
- 入力が主に画像・視線・骨格など（比較背景としては別）

---

## 3. 主要先行研究（国内・海外）
> できるだけ **方法 / 評価指標 / データセット** を揃えて整理。  
> データ公開性は臨床系で制約が強いため「公開/非公開/不明」を明示。

### 3.1 国内（日本語）
#### [JP-1] Nakamura ら（2025, SICE 東北支部研究会資料）
- タスク: ADOS-2 会話テキストから **4分類（ASD / Spectrum / Gray-zone / TD）**
- 入力: ADOS-2 の「検査者−被験者」会話（日本語）
- データ: 合計 96（ASD 28 / Spectrum 24 / Gray-zone 24 / TD 20）
- 特徴量/モデル:
  - 統計特徴（フィラー頻度、発話比率、品詞頻度など）
  - BERT 由来の文脈一貫性/文類似度などを数値化
  - LightGBM（多クラス） + SHAP
- 評価指標: Accuracy / Precision / Recall / F1（クラス別）
- 代表結果: Accuracy=0.49、ASDクラス F1=0.53（報告値）
- 公開性: データ/コードは明示的公開なし（学会資料PDFは公開）

Ref:
- PDF: https://www.topic.ad.jp/sice/htdocs/papers/353/353-9.pdf

---

### 3.2 海外（英語・スペイン語・韓国語など）
#### [INT-1] Hu et al.（2025, *npj Digital Medicine*）
- タスク: ADOS-2 Module 4 対話から **ADOS項目A4（常同的/独特な言語使用）の有無（二値）** を推定
- 入力: Examiner–Participant dialogue（対話転記）  
  ※重要ポイント: **話者分離（speaker diarization）品質が性能に強く影響**
- データ: Caltech ADOS 音声/映像由来  
  参加者 35 名 / 録音 44 本 → シナリオ単位のサンプル（最終 463 など、論文記載に基づく）
- モデル:
  - 生成LLM（GPT系、Gemini Flash、Mistral、Qwen 等）を **ゼロショット**で評価
  - ベースライン: BERT / RoBERTa / XLNet / ALBERT / DistilBERT など
- 評価指標: Accuracy / PPV / Sensitivity(Recall) / F1
- 代表結果（報告値）:
  - w/ human diarization + GPT: Accuracy≈0.82, F1≈0.8657
  - w/o diarization: F1 が大きく低下
- 公開性:
  - コード: 公開（GitHub）
  - データ: 臨床データのため公開制約（少なくとも論文上は一般公開として配布していない）

Ref:
- Paper (PDF): https://www.nature.com/articles/s41746-025-02133-9.pdf  
- Code: https://github.com/cbhu523/chatgpt_ASD_diagnosis

---

#### [INT-2] Altozano et al.（2026, *IEEE JBHI*）※オンライン先行 2025 が流通
- タスク: 保護者の「自由回答（12問）」から **ASD/TD 二値分類**
- 入力: 口頭自由回答の転記（スペイン語、論文では英訳も提示）
- データ: 保護者 51 名（TD児の保護者 26 / ASD児の保護者 25）※報告に基づく
- モデル/設計:
  - 埋め込みモデル + 分類ヘッド（凍結/更新の比較）
  - 小型ローカルPLM（mRoBERTa base など）
  - GPT-4o をゼロショット評価（“質問+回答”を明示する入力形式などを比較）
  - 被験者単位リークを防ぐ **ネストCV（外側5-fold / 内側4-fold）**
  - 質問単位モデル→投票で被験者単位へ集約
- 評価指標: Accuracy / TPR / TNR / ROC-AUC（主指標として提示）
- 代表結果（報告値）:
  - 最良条件で ROC-AUC=1.00（小標本・設計上の注意は必要）
- 公開性: データ/コード公開は明示が弱い（要確認）

Ref:
- PubMed: https://pubmed.ncbi.nlm.nih.gov/40815586/  
- Full text（掲載/転載元の一例）: https://www.researchgate.net/publication/394503219_Enhancing_Psychological_Assessments_with_Open-Ended_Questionnaires_and_Large_Language_Models_An_ASD_Case_Study

---

#### [INT-3] Mun et al.（2024, arXiv / Interspeech 流通）
- タスク: ASD児の発話（ASR/人手転記）から **Social Communication Severity（連続値）** を回帰推定
- 入力: 子ども発話の転記テキスト（韓国語）
- データ: ASD 168 / TD 40（ASR微調整などの記載に基づく）  
  重症度ラベルは SLP 複数名評価の平均など（論文記載に基づく）
- パイプライン:
  - ASR（wav2vec2 / Whisper）→ 転記 → PLM（KR-BERT / KLUE RoBERTa / KR-ELECTRA）
  - low-resource 条件で manual prompt / p-tuning（PEFT）を比較
- 評価指標: Pearson correlation coefficient（PCC）
- 代表結果（報告値）:
  - 条件によって PCC が大きく変動（高い値〜不安定まで幅）
- 公開性: データ公開は不明/制約が強い可能性

Ref:
- arXiv: https://arxiv.org/abs/2409.00158  
- PDF: https://arxiv.org/pdf/2409.00158

---

#### [INT-4] Lee et al.（2024, LREC-COLING）※データ資源（韓国語）
- 位置づけ: **ASD 音声/言語コーパス整備**（推定モデル研究の土台）
- 公開性・取得条件は論文に依存（DUA等の可能性あり）

Ref:
- ACL Anthology: https://aclanthology.org/2024.lrec-main.1318/  
- PDF: https://aclanthology.org/2024.lrec-main.1318.pdf

---

#### [INT-5] Feng et al.（2024, arXiv/OpenReview）
- 位置づけ: ASD児を含む **臨床観察会話（child-adult interaction）** を LLM で多タスク理解  
  ※ASD/traits 推定そのものではないが、臨床談話×LLMの代表例
- タスク例: 活動/観察ラベル、言語スキル、年齢等を推定（F1で評価）
- 公開性: 元コーパス制約に依存

Ref:
- arXiv PDF: https://arxiv.org/pdf/2411.10761  
- OpenReview PDF: https://openreview.net/pdf?id=3Pynfd5HIy

---

#### [補足] Mukherjee et al.（2023, IJACSA）
- ASD関連を “親の対話文” から検出と主張するが、データ構築・再現性の記載が弱く、臨床/研究のベンチマークとしては慎重扱い推奨。

Ref:
- PDF（例）: https://pdfs.semanticscholar.org/dbe4/4060dee07cfd598d39d2035593ee3fe2fdfc.pdf  
- Journal page: https://thesai.org/Publications/ViewPaper?Code=IJACSA&Issue=10&SerialNo=41&Volume=14

---

## 4. 比較表（方法・評価・データセット）
| ID | 研究 | 入力（談話） | 出力（ASD関連） | 言語 | データ規模（報告） | 中核モデル | 指標 | 代表性能（報告） | 公開性 |
|---|---|---|---|---|---:|---|---|---|---|
| JP-1 | Nakamura 2025 | ADOS-2会話転記 | 4分類 | 日本語 | 96 | BERT由来特徴 + LightGBM | Acc/F1 | Acc=0.49 | PDFのみ |
| INT-1 | Hu 2025 npj | ADOS-2対話転記（話者分離重要） | ADOS A4 二値 | 英語 | 35人/44録音→463サンプル等 | ゼロショLLM + diarization 比較 | Acc/PPV/Recall/F1 | F1≈0.8657（human diarization） | code○/data× |
| INT-2 | Altozano 2026 JBHI | 保護者自由回答（口頭→転記） | ASD/TD 二値 | 西語 | 51 | 埋め込み/PLM + GPT-4o ゼロショ | Acc/TPR/TNR/AUC | AUC=1.00（最良条件） | 不明 |
| INT-3 | Mun 2024 | 子ども発話（ASR/人手転記） | 重症度回帰（連続） | 韓国語 | ASD168/TD40等 | ASR + KR-PLM + prompt/p-tuning | PCC | 条件依存（高PCC報告あり） | 不明 |
| INT-5 | Feng 2024 | 臨床観察会話転記 | 多タスク（技能/属性など） | 英語 | 複数コーパス | LLMプロンプト | F1 | タスク別に幅 | 不明 |

---

## 5. 重要な観察（「刺さる」ギャップの言語化）
### 5.1 既存研究の“中心線”
- **限定ターゲット（ADOS項目など）**は成立しやすい  
  - タスク定義が明確、臨床的解釈もつけやすい（Hu 2025）
- **二値分類（ASD/TD）**は報告が多いが、  
  - 小標本・非公開データ・外部検証不足が残りやすい（Altozano 2026 など）
- **重症度回帰**は可能性があるが、  
  - ASR/転記誤差・プロンプト設計でブレが大きく、評価の安定性が課題（Mun 2024）

### 5.2 明確に薄い（＝ブルーオーシャンになり得る）領域
- **談話 → 多次元のASD traits（例：AQ/SRS、または複数ドメインの連続スコア）**  
  を **再現可能な評価設計（リーク防止、外部検証、ベースライン比較、ロバスト性評価）** で揃えた研究が薄い。
- 特に **日本語談話**では、生成LLMを主役に据えた比較評価はまだ限定的（少なくとも公開資料としては）。

> イントロ用ギャップ文（草案）
> 「談話からLLM/PLMでASD関連指標を推定する研究は増えているが、公開可能な評価設計の下で、多次元の“特性プロファイル”を再現可能に推定・解釈する枠組みはまだ不足している。」

---

## 6. 研究設計への示唆（私たちの強みを最大化するなら）
### 6.1 “診断”ではなく “特性（traits）推定”として立て付ける
- 臨床的・倫理的な議論が通りやすい（支援・研究用途、スクリーニング補助の位置づけ）

### 6.2 追加すべき評価軸（差別化ポイント）
- **リーク防止**: subject-wise split（被験者単位で完全分離）
- **外部検証**: 別収録条件/別コーパス/別方言
- **ロバスト性**: ASR誤差・話者分離誤差を注入して性能変動を計測（Hu 2025 を踏襲拡張）
- **説明可能性**: どの談話特徴が効いたか（語用論・相互行為特徴量 + LLMの判断根拠を分離して扱う）

---

## 7. タイムライン（研究潮流）
```mermaid
timeline
  title Discourse × Language Models × ASD: confirmed milestones
  2024 : Mun et al. (ASR→transcript→PLM) predicts severity (regression)
  2025 : Nakamura et al. (JP ADOS-2 text) BERT-features + LightGBM + SHAP
  2025 : Hu et al. (npj DM) zero-shot LLM for ADOS item (A4); diarization critical
  2026 : Altozano et al. (IEEE JBHI) open-ended questionnaires + LLMs for ASD/TD
````

---

## 8. 参考リンク集

[JP]
- Nakamura et al. 2025 (SICE 東北支部 353-9 PDF)
  https://www.topic.ad.jp/sice/htdocs/papers/353/353-9.pdf

[INT: ADOS-2 dialogue × LLM (npj Digital Medicine, 2025)]
- Hu et al. 2025 (npj Digital Medicine) PDF
  https://www.nature.com/articles/s41746-025-02133-9.pdf
- Code (GitHub)
  https://github.com/cbhu523/chatgpt_ASD_diagnosis

[INT: Open-ended questionnaire × LLM (IEEE JBHI, 2026)]
- Altozano et al. 2026 (PubMed)
  https://pubmed.ncbi.nlm.nih.gov/40815586/
- Full text (example)
  https://www.researchgate.net/publication/394503219_Enhancing_Psychological_Assessments_with_Open-Ended_Questionnaires_and_Large_Language_Models_An_ASD_Case_Study

[INT: Severity regression (2024)]
- Mun et al. 2024 arXiv
  https://arxiv.org/abs/2409.00158
  https://arxiv.org/pdf/2409.00158

[INT: Korean ASD speech resource (LREC-COLING 2024)]
- Lee et al. 2024 (ACL Anthology)
  https://aclanthology.org/2024.lrec-main.1318/
  https://aclanthology.org/2024.lrec-main.1318.pdf

[INT: LLM analysis of child-adult interactions (2024)]
- Feng et al. 2024 arXiv
  https://arxiv.org/pdf/2411.10761
- OpenReview PDF
  https://openreview.net/pdf?id=3Pynfd5HIy

[Supplement (lower confidence / reproducibility)]
- Mukherjee et al. 2023 (IJACSA) PDF (example mirror)
  https://pdfs.semanticscholar.org/dbe4/4060dee07cfd598d39d2035593ee3fe2fdfc.pdf
  https://thesai.org/Publications/ViewPaper?Code=IJACSA&Issue=10&SerialNo=41&Volume=14
  