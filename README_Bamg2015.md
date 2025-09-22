# ASD / TD — Pragmatics & MLU Reproduction

英語公開コーパス（TalkBank/CHILDES, ASDBank）を用いた  
**Bang & Nadig (2015)** 英語サブセット（母親発話）**MLU再現**と、MVP（語用論指標）のプロトタイプです。

- 論文: Bang, J. & Nadig, A. (2015), *Autism Research*. DOI: **10.1002/aur.1440**  
  PDF（TalkBank掲載）: https://talkbank.org/asd/access/0docs/Bang2015.pdf
- MVPレポート: https://leadlea.github.io/asd/ASD_TD_MVP_Report.html

---

## ✨ What’s new

- `bn2015_dual_run.py` … **strict（min=1）** と **robust（min=2）** を **一括実行**し、  
  CSV/MDを吐き出し、**docs/** に比較 **HTML** を自動生成
- `dual_bn2015.yaml` … 設定1ファイルで **両モード**を制御（MVP比較・論文PDFリンク込み）
- `reproduce/bang_nadig_2015/parse_cha_compute_mlu.py` … 再現用のコア実装（母親UID・多数決集約・%mor優先など）

---

## 📁 Repository layout

```
.
├─ Nadig/                          # .cha transcripts（ローカル/非公開推奨）
├─ docs/
│   └─ bn2015_reproduction.html    # paper vs strict vs robust vs MVP の比較HTML（自動生成）
├─ reports/reproduction/bang_nadig_2015/
│   ├─ group_summary_strict.csv    # strict の集計
│   ├─ group_summary_robust.csv    # robust の集計
│   ├─ bn2015_report_strict.md     # strict の短いMDレポート
│   └─ bn2015_report_robust.md     # robust の短いMDレポート
├─ reproduce/bang_nadig_2015/
│   ├─ parse_cha_compute_mlu.py    # MLU計算スクリプト（再現用）
│   └─ reproduce_bang_nadig_2015.yaml
├─ bn2015_dual_run.py              # ← 両モード実行＋HTML生成ドライバ
├─ dual_bn2015.yaml                # ← 1ファイルでstrict/robust制御
└─ README.md
```

> **GitHub Pages** を使う場合は、リポジトリ設定で  
> **Pages → Source: “Deploy from a branch” / Branch: `main` / Folder: `/docs`** を選べば  
> `docs/bn2015_reproduction.html` がそのまま公開されます。

---

## ⚙️ Setup

```bash
python -V               # 3.9+
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt  # ない場合は pyyaml だけでも動作します
# pip install pyyaml
```

> **データ配置**: `Nadig/` 直下（または `dual_bn2015.yaml` の `transcripts_dir` を変更）

---

## ▶️ Quick run (dual)

**strict（min=1）** と **robust（min=2）** を連続実行し、比較HTMLを生成します。

```bash
python bn2015_dual_run.py --config dual_bn2015.yaml
```

出力（抜粋）:
```
reports/reproduction/bang_nadig_2015/
  group_summary_strict.csv
  group_summary_robust.csv
  bn2015_report_strict.md
  bn2015_report_robust.md
docs/
  bn2015_reproduction.html
```

---

## 🔬 Modes: strict vs robust

- **Strict**（厳密再現）  
  - `min_utterance_len_tokens = 1`  
  - `exclude_pure_intj = false`（あいづち等も含める）  
  - 先行研究の **“同じデータに同じ解析で近い数値”** を目標に提示
- **Robust**（感度分析）  
  - `min_utterance_len_tokens = 2`（1語のみの発話を除外）  
  - `exclude_pure_intj = true`（%mor で intj のみの発話は除外）  
  - **1語発話/あいづち**によるMLUの下振れを抑止する近似（参考提示）

> **説明の仕方（先生向け）**  
> 主結果は **strict** を正式な“検算”、**robust** は“近似の頑健性確認”として**別枠**で併記。

---

## 🧪 Reproduction core (MLUw)

- **スピーカ**: 母親（`MOT`）のみ  
- **集計**: **母親単位**でMLU（語数/発話数）を平均 → 群（ASD/TYP）平均±SD  
- **トークン**: `%mor` 優先（見つからない発話は表層へフォールバック）  
- **不要語**: 句読点・コード（`:+` や `&...`、`xxx/yyy/www`）除外  
- **母親ラベル**: `@ID(CHI)` → `@ID(全体)` → `@Types` の順で ASD/TYP を推定  
- **母親UID**: `@ID(CHI)[1]=study, [9]=code` を優先し、フォールバック実装  
- **同一母親の複数セッション**: **多数決**（空ラベルは無視）で群ラベル決定

> `%mor` が取れずにゼロ発話となるセッションは、**表層語でのユニバーサル・バックオフ**で再計算します（セッション丸落ち回避）。

---

## 🧾 Config: `dual_bn2015.yaml`

```yaml
paper:
  title: "Bang & Nadig (2015) Autism Research — English subset (Mother input)"
  doi: "10.1002/aur.1440"
  pdf_url: "https://talkbank.org/asd/access/0docs/Bang2015.pdf"

targets:            # 先生の“検算”元値（Table 2）
  ASD: { mean: 5.06, sd: 0.92 }
  TYP: { mean: 5.40, sd: 0.81 }

base:
  dataset:
    transcripts_dir: "./Nadig"
    include_language_codes: ["eng"]
    include_speakers: ["MOT"]
    group_labels: ["ASD", "TYP"]
    strict_english_only: false
    aggregate_by_mother: true
  preprocess:
    use_mor_tokens: true
    lowercase: true
    use_gem_window: false
    min_utterance_len_tokens: 1     # strict基準（robustで上書き）
    exclude_tokens_regex: '^(?:[:+].*|&.*|xxx|yyy|www)$'
    exclude_pure_intj: false        # strict基準（robustで上書き）
  tolerance:
    absolute_mean: 0.15
    relative_mean: 0.05
  outputs_root: "reports/reproduction/bang_nadig_2015"

mvp:                 # あなたのMVPとの比較欄（HTMLに出ます）
  label: "Your MVP"
  url: "https://leadlea.github.io/asd/ASD_TD_MVP_Report.html"
  values:
    ASD: { mean: null, sd: null }
    TYP: { mean: null, sd: null }

modes:
  - name: strict
    outputs_suffix: "strict"
    preprocess_overrides:
      exclude_pure_intj: false
      min_utterance_len_tokens: 1
  - name: robust
    outputs_suffix: "robust"
    preprocess_overrides:
      exclude_pure_intj: true
      min_utterance_len_tokens: 2

docs:
  html_out: "docs/bn2015_reproduction.html"
```

---

## 📊 docs/ HTML の中身

- テーブルで **Paper / Strict / Robust / MVP** を横並び比較
- ヘッダに **DOI** と **PDFリンク** を表示
- 使ったルール（min・intj除外など）を明記  
→ そのまま先生にURLで共有できます（GitHub Pages 推奨）

---

## 📝 Recommended `.gitignore`

出力と元データは太りやすいので、基本はコミットしないのが無難です。

```
__pycache__/
*.pyc
.venv/
.DS_Store
Nadig/
reports/
*.log
```

> どうしてもレポート等を残したい場合は、`reports/reproduction/bang_nadig_2015/` の  
> `group_summary_*.csv` と `bn2015_report_*.md` のみを選んで add してください。

---

## 🗒️ Notes for replication write-up

- **本編（strict）**を主結果として提示（min=1、intj除外なし）  
- **robust**は“1語発話/あいづちの影響を抑えた感度分析”として別枠  
- `%mor` が見つからずゼロ発話のセッションは、表層語で**バックオフ再計算**  
- 3セッション（例: `Nadig/120/126/133`）は **有効発話ゼロ**のため欠測（群平均に影響なし）と注記  
- CLANのMLUwと自作前処理の**境界規則差**（リペア/maze・省略形など）がわずかな差の主因

---

## 📄 Citation

If you use this code or results, please cite:

- Bang, J., & Nadig, A. (2015). *Autism Research*. https://doi.org/10.1002/aur.1440  
- TalkBank/CHILDES (ASDBank) — data licenses and usage terms.

---

## 🧑‍⚖️ License

See `LICENSE` (if absent, treat as “code for research demo; no warranty”).
