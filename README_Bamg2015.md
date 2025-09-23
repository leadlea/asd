# ASD/TD — Reproduction & MVP Validation (ASDBank English)

本READMEは、**同一データに同一解析を適用して先行知見を検算**し、MVP（語用論・語彙指標の組合せ）の妥当性を点検するための実行手順と結果の記録です。  
データは ASDBank（TalkBank/CHILDES）の **英語 .cha**（Nadig コーパス）を用いています。

---

## TL;DR（結論先出し）

- **子ども発話（CHI）での検算**  
  - **MLU**: ASD=3.283, TYP=3.227 → *d*=+0.064（差はごく小）  
  - **TTR**: ASD=0.5615, TYP=0.5017 → *d*=+0.560（中程度）。Welch *t*=1.476, *p*=0.155, 95%CI=[−0.022, 0.141]（方向はASD高だが有意には至らず）  
  - **NDW（等量化）**: NDW@100 で ASD=54.4, TYP=60.8 → *d*=−0.529（中程度）、Welch *t*=−1.327, *p*=0.201, 95%CI=[−16.32, 3.41]  
    - 感度: NDW@50 *d*=−0.398、NDW@150 *d*=−0.509（**Nを変えても ASD < TYP が安定**）
- **示唆**: **MLU単独では差は弱い**一方、**語彙の比率的多様性（TTR）はASDで高め**、**語彙種類の総量（NDW）はASDで少なめ**という相補パターンを確認。  
  → **複数指標の組合せ**で差を捉える**現MVPの方針は妥当**。

> なお、**母親発話（MOT）のMLU再現**は Bang & Nadig (2015) 英語小計の**検算対象**として別途整備し、数値合わせの調整は行わず「strict（min=1）」を主、感度として「robust（min=2, intj除外）」を併記する方針です。

---

## データ・ライセンス上の注意（重要）

- **ASDBank/TalkBank の .cha テキストを日本語に翻訳して共有・公開することは規約上できません**。本リポジトリでは**英語 .cha のみ**を解析対象とします。  
- 実音声（.wav）は未使用。**「音声/プロソディ」は、.cha 上のフィラー・ポーズ記号等から導く代理指標**として扱っています（README/コードにも明示）。

---

## 環境と配置

- Python 3.12（3.9+ 推奨）  
- 依存：`PyYAML`（検定を出す場合は `scipy` も）  
- ルート直下に `Nadig/` を置き、配下に `.cha` がある想定
  ```
  .
  ├─ Nadig/                     # .cha transcripts（ローカル/非公開）
  ├─ reproduce/bang_nadig_2015/
  │   ├─ parse_cha_compute_mlu.py
  │   ├─ compute_ttr_ndw.py
  │   ├─ compute_ndw_atN.py
  │   └─ reproduce_bang_nadig_2015.yaml
  └─ reports/reproduction/bang_nadig_2015/  # 出力先
  ```

セットアップ例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install PyYAML scipy  # 検定を出すなら scipy も
```

---

## 今日の作業ログ（時系列）

### 1) 子ども発話（CHI）で MLU を計算（%mor優先）
目的：MVP（子ども発話から ASD/TD を判別）の文脈に即して、まず **CHI** を主対象に設定。  
設定要点：
- 話者=**CHI**
- トークン= **%mor を優先**（見つからない発話は**表層語にフォールバック**）
- 最小発話長=1語（厳格）
- 言語=英語（`include_language_codes: ["eng"]`, `strict_english_only: false`）
- GEM 窓は有効にしても **今回の .cha は時刻未記入が多く、実質オフ同等**

実行:
```bash
python reproduce/bang_nadig_2015/parse_cha_compute_mlu.py   --config reproduce/bang_nadig_2015/reproduce_bang_nadig_2015.yaml
```

主出力:
- `reports/.../per_child_mlu.csv`
- `reports/.../group_summary.csv`
- `reports/.../bn2015_reproduction_report.md`

要約（CHI/MLU）:
- ASD=**3.283**（n=13）, TYP=**3.227**（n=25） → **d=+0.064**（差はごく小）

---

### 2) 語彙多様性（TTR）と種類語数（NDW）を追加
目的：MLU単独で差が弱いため、**語彙系の補助指標**で群差を点検。

実行:
```bash
# TTR/NDW（総語数ベース）
python reproduce/bang_nadig_2015/compute_ttr_ndw.py

# 等量化 NDW@N（発話量依存性を抑制）
python reproduce/bang_nadig_2015/compute_ndw_atN.py --N 50
python reproduce/bang_nadig_2015/compute_ndw_atN.py --N 100
python reproduce/bang_nadig_2015/compute_ndw_atN.py --N 150
```

結果（CHI）:
- **TTR**: ASD=**0.5615**（n=13）, TYP=**0.5017**（n=25） → **d=+0.560**  
  Welch *t*=1.476, *p*=0.155, 95%CI=[−0.022, 0.141]
- **NDW@50**:  ASD=32.6, TYP=35.0 → **d=−0.398**  
- **NDW@100**: ASD=**54.4**, TYP=**60.8** → **d=−0.529**  
  Welch *t*=−1.327, *p*=0.201, 95%CI=[−16.32, 3.41]
- **NDW@150**: ASD=69.4, TYP=79.0 → **d=−0.509**

解釈：
- **TTRはASDで高め**（比率の多様性）。一方で **NDWはASDで低め**（種類語の総量）  
- **等量化（NDW@N）でも方向が保たれる** → 量依存性の説明だけでは崩れない相補パターン

---

### 3) （補助）母親発話（MOT）での B&N (2015) 検算セット
目的：先生の宿題「**同じデータに同じ解析で同様の数値が出るか**」の確認（母親MLU：英語小計）。  
方針：
- **strict（min=1, intj含む）**を主結果、**robust（min=2, intj除外）**は感度として別枠表示
- **数値合わせの調整は行わない**（ルールは事前固定）

（実行スクリプト・HTML出力は別紙 `bn2015_dual_run.py` 等、MOT用に整備。必要時に再掲。）

---

## 再現設定（要点）

`reproduce/bang_nadig_2015/reproduce_bang_nadig_2015.yaml`（抜粋・CHI版）
```yaml
dataset:
  transcripts_dir: "./Nadig"
  include_language_codes: ["eng"]
  include_speakers: ["CHI"]
  group_labels: ["ASD", "TYP"]
  strict_english_only: false
preprocess:
  use_mor_tokens: true
  lowercase: true
  min_utterance_len_tokens: 1
  exclude_tokens_regex: '^(?:[:+].*|&.*|xxx|yyy|www)$'
  # GEMウィンドウ指定なし（時刻欠損が多いため実質全発話採用）
```

実装の注意点：
- `%mor` が見つからず0発話になるセッションは**表層語にユニバーサル・バックオフ**  
- トークンは **英字＋省略形（don’t等）**のみ採用、句読点・コード・フィラー等は除外  
- 群ラベルは `@ID(CHI) → @ID(全体) → @Types` の順で推定（TYP=TD相当）  
- 個体UID（子／母）は `@ID` の情報から安定化（重複や空を回避）

---

## 先生への説明ポイント（短文）

- **英語・ASDBank・CHI発話で検算**したところ、**MLU単独は差小**。  
- **TTRはASDで高め**、**NDWはASDで低め**で、**等量化NDW@Nでも方向が安定**。  
- よって、**単一指標ではなく複数の語用論・語彙指標の組み合わせ**で差を捉えるMVP方針が妥当。  
- 日本語展開では指標・前処理が英語と異なるため（終助詞・談話標識・ゼロ代名詞等）、英語での妥当性を基準線として独立に設計・検証します。  
- ※ **ASDBank の日本語翻訳・共有は不可**（規約上）。英語のみで検算し、日本語は別ルートで最小検証を行います。

---

## 参考（出力ファイル）

- `reports/reproduction/bang_nadig_2015/per_child_mlu.csv`  
- `reports/reproduction/bang_nadig_2015/per_child_ttr_ndw.csv`  
- `reports/reproduction/bang_nadig_2015/per_child_ndw_at100.csv` ほか NDW@N  
- `reports/reproduction/bang_nadig_2015/group_summary.csv`  
- `reports/reproduction/bang_nadig_2015/bn2015_reproduction_report.md`

---

## 既知の限界・想定差

- CLANの厳密なMLUw定義と完全一致は保証しない（修復語/maze、縮約の扱い等の境界差）。  
- Nadig英語 .cha は `@Bg/@Eg`（時刻）未記入が多く、GEM窓の厳密適用は困難（今回は全発話採用に相当）。  
- サンプル数が小さいため、**効果量中心の記述**とし、統計的有意は探索的に扱う。

---

## Citation
- Bang, J., & Nadig, A. (2015). Autism Research.  
- TalkBank/CHILDES (ASDBank) — data licenses and usage terms.
