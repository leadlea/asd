# ASD / TD — Pragmatics & MLU Reproduction

英語公開コーパス（TalkBank/CHILDES, ASDBank）を用いた  
**Bang & Nadig (2015)** 英語サブセット（母親発話）**MLU再現**と、MVP（語用論指標）のプロトタイプです。

**Public report (GitHub Pages)** → https://leadlea.github.io/asd/compare.html  
**One-liner to reproduce & publish** → `make reproduce_bn2015_log && make show_repro`

---

## 重要な注記（群の定義）
本リポジトリで用いる「ASD/TYP（TD）」の群ラベルは子どもの診断群を指します。
「母親」「母親発話」はASD/TYP児に対する母親の発話（入力）を意味し、母親自身の診断を示すものではありません。

- 論文: Bang, J. & Nadig, A. (2015), *Autism Research*. DOI: **10.1002/aur.1440**  
  PDF（TalkBank掲載）: https://talkbank.org/asd/access/0docs/Bang2015.pdf
- MVPレポート: https://leadlea.github.io/asd/ASD_TD_MVP_Report.html

---

## ✨ What’s new

- `bn2015_dual_run.py` … **strict（min=1）** と **robust（min=2）** を **一括実行**し、  
  CSV/MDを吐き出し、**docs/** に比較 **HTML** を自動生成（ビルド情報付き）
- `dual_bn2015.yaml` … 設定1ファイルで **両モード**を制御（論文PDFリンク/対象値込み）
- **公開CSVを `docs/assets/bn2015/` に自動コピー**（Pagesで直接ダウンロード可）

---

## 📁 Repository layout（抜粋）

```
.
├─ Nadig/                           # .cha transcripts（ローカル/非公開推奨）
├─ docs/
│  ├─ compare.html                  # Paper vs Strict/Robust (+ ΔMean/ΔSD)
│  └─ assets/bn2015/
│      ├─ group_summary_strict.csv  # strict の集計（公開用CSV）
│      └─ group_summary_robust.csv  # robust の集計（公開用CSV）
├─ reports/reproduction/bang_nadig_2015/   # ローカル成果（公開しない想定）
│  ├─ group_summary_strict.csv
│  ├─ group_summary_robust.csv
│  ├─ bn2015_report_strict.md
│  └─ bn2015_report_robust.md
├─ bn2015_dual_run.py               # ← 両モード実行＋HTML生成ドライバ
├─ dual_bn2015.yaml                 # ← 1ファイルでstrict/robust制御
└─ README.md / README_Bamg2015.md
```

> **GitHub Pages** 設定：**Settings → Pages** で  
> **Source: “Deploy from a branch” / Branch: `main` / Folder: `/docs`**。  
> 直接公開されるのは `docs/` 配下のみ（CSVは `docs/assets/bn2015/` に配置）。

---

## ⚙️ Setup

```bash
python -V               # 3.9+ 推奨
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```
> **データ配置**: `Nadig/` 直下（または `dual_bn2015.yaml` の `transcripts_dir` を変更）

---

## ▶️ Quick run（strict + robust 一括 & 公開）

最小コマンド：

```bash
make reproduce_bn2015_log && make show_repro
# 生成物: docs/compare.html と docs/assets/bn2015/*.csv
```

（直接呼び出しでも可）
```bash
python bn2015_dual_run.py --config dual_bn2015.yaml
```

---

## 🔬 Modes: strict vs robust

- **Strict**（厳密再現）  
  - `min_utterance_len_tokens = 1`  
  - `exclude_pure_intj = false`（あいづち等も含める）
- **Robust**（感度分析）  
  - `min_utterance_len_tokens = 2`（1語のみの発話を除外）  
  - `exclude_pure_intj = true`（%mor で intj のみの発話は除外）

> **提示方針**：**strict** を“検算”、**robust** は“頑健性確認”。ルールで合わせに行かず、差分はNotesで説明。

---

## 🧪 Reproduction core (MLUw)

- **Speaker**: 母親（`MOT`）のみ（`include_speakers=["MOT"]`）  
  → 母親発話を含まないセッション（例 `120/126/133.cha`）は自動除外。  
- **集計**: **母親ごと**に MLUw（語/発話）を平均 → 群（ASD/TYP）平均±SD  
- **トークン**: `%mor` 優先（なければ表層語にフォールバック）  
- **ウィンドウ**: `@Bg/@Eg` があれば適用。無ければ全区間（Notesに明記）  
- **母親ラベル決定**: `@ID(CHI)` → `@ID(全体)` → `@Types` の順で ASD/TYP 推定  
- **SD**: 標本標準偏差（n−1）

---

## 🧾 Config: `dual_bn2015.yaml`（主要部）

```yaml
paper:
  title: "Bang & Nadig (2015) Autism Research — English subset (Mother input)"
  doi: "10.1002/aur.1440"
  pdf_url: "https://talkbank.org/asd/access/0docs/Bang2015.pdf"

targets:            # Table 2 (EN, mother MLU)
  ASD: { mean: 5.06, sd: 0.92 }
  TYP: { mean: 5.40, sd: 0.81 }

base:
  dataset:
    transcripts_dir: "./Nadig"
    include_language_codes: ["eng"]
    include_speakers: ["MOT"]
    group_labels: ["ASD", "TYP"]
  preprocess:
    use_mor_tokens: true
    lowercase: true
    use_gem_window: false
    min_utterance_len_tokens: 1
    exclude_tokens_regex: '^(?:[:+].*|&.*|xxx|yyy|www)$'
    exclude_pure_intj: false
  outputs_root: "reports/reproduction/bang_nadig_2015"

modes:
  - name: strict
    outputs_suffix: "strict"
    preprocess_overrides: { exclude_pure_intj: false, min_utterance_len_tokens: 1 }
  - name: robust
    outputs_suffix: "robust"
    preprocess_overrides: { exclude_pure_intj: true,  min_utterance_len_tokens: 2 }

docs:
  html_out: "docs/Compare.html"
  publish_csv: true
  csv_public_dir: "docs/assets/bn2015"
```

---

## 📊 公開HTML（Compare.html）
- テーブル：**Paper / Strict / Robust** を横並び、**ΔMean / ΔSD** を表示
- Notes に**実行条件**・**CSVリンク**・**Speakerフィルタ（MOTのみ）**を明記
- フッターに **Generated on …, commit abc123** を自動追記

---

## 📝 Recommended `.gitignore`

```
__pycache__/
*.pyc
.venv/
.DS_Store
Nadig/
reports/
logs/
# ※ 公開CSVは除外しない
!docs/assets/**/*.csv
```

---

## 🗒️ 検算サマリー（Bang & Nadig, 2015：英語・母親 MLU）

**目標値（Table 2, English subset, mother MLU）**  
ASD = 5.06 (SD 0.92), TYP = 5.40 (SD 0.81)

本実装（Robust）の例：ASD **4.90±0.68**, TYP **5.38±0.82** （Δmean −0.16 / −0.02）

---

## 📄 Citation

If you use this code or results, please cite:
- Bang, J., & Nadig, A. (2015). *Autism Research*. https://doi.org/10.1002/aur.1440  
- TalkBank/CHILDES (ASDBank) — data licenses and usage terms.
