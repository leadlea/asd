# BN2015 再現 + 語用論メタ指標ダッシュボード

## 目的
- 山下先生／和田先生に、**Bang & Nadig (2015; 以下 BN2015)** の英語再現結果と、
  追加実装した **語用論（Pragmatics）メタ指標**を **1枚のHTML** で見てもらう。
- **日本語 README** だけ読めば、再現の流れ・指標の定義・出典が分かる。

## 概要
- 対象データ: TalkBank **Nadig (English, 100番台)**。偶数=ASD, 奇数=TYP。
- 再現: BN2015 の **T2（9分窓）** を 11/11 subject にそろえて再集計。
- 追加実装（CHIのみ）:
  - **Questions（All/WH/Yes-No）** …… *per utter*
  - **Discourse Markers（Fill/Contrast/Causal/Shift）** …… *per 100 utter*
  - **Mental-state（総数）** …… *per 100 words*
  - **メタ解析CSV** …… *mean/sd/n と Hedges’ g（95%CI）*

## フォルダ構成（公開時）
```
.
├─ docs/
│  ├─ index.html                 # ダッシュボードのリンク
│  └─ bn2015_dashboard.html      # 生成物（GitHub Pages で公開）
├─ src/features/
│  ├─ pragmatics_from_cha.py     # Nadig .cha → CHI の語用論指標を集計（ASD/TYP）
│  └─ pragmatics_basic.py        # 既存の簡易版（任意）
├─ make_dashboard.py             # ダッシュボード生成
├─ dual_bn2015.yaml              # 既存の再現設定
├─ README_JA.md                  # このファイル
└─ data/                         # データ置き場（原則リポジトリには含めない）
   ├─ raw/asd/Nadig/*.cha        # Nadig 英語（取得元から各自取得）
   └─ processed/                 # スクリプトで再生成できる中間物
```

## 依存パッケージ（最小）
```bash
python -m venv .venv-bn2015
source .venv-bn2015/bin/activate
pip install -U pip pandas numpy matplotlib pyyaml
```

## 再現手順（ローカル）

### 1) CHI の語用論指標を生成（11/11 subject に制限）
```bash
python src/features/pragmatics_from_cha.py   --nadig_dir data/raw/asd/Nadig   --restrict_to_dyads dyads.bn2015.full.csv   --out_csv data/processed/pragmatics_child_group.csv   --byfile_out_csv data/processed/pragmatics_child_byfile.csv   --meta_out data/processed/pragmatics_meta.csv
```

### 2) ダッシュボードを生成（`docs/`に書き出し）
```bash
python make_dashboard.py   --dyads dyads.bn2015.full.csv   --desc  out/bn2015/table3_descriptives_en.csv   --ttest out/bn2015/table2_en_ttests.csv   --out   docs   --prag_child_grp data/processed/pragmatics_child_group.csv   --prag_meta      data/processed/pragmatics_meta.csv
```

- 生成された **docs/bn2015_dashboard.html** を GitHub Pages で公開（下記参照）。

## GitHub Pages で公開
1. GitHub の **Settings → Pages** を開く  
2. **Source: “Deploy from a branch”**, **Branch: `main` / Folder: `/docs`** を選択  
3. 保存後、数十秒で公開URL（`https://<user>.github.io/<repo>/`）が発行

## 語用論の指標定義（CHI）
- Questions（All / WH / Yes-No）:  
  - All = WH ∪ Yes-No、分母は CHI の発話数 `n_utt`、単位 *per utter*
- Discourse Markers: Fill / Contrast / Causal / Shift（単位 *per 100 utter*）  
  - **Contrast 辞書**（拡張済）:  
    `but, however, though, although, yet, whereas, instead, but then, even so, on the other hand,
     in contrast, nevertheless, nonetheless, still`
- Mental-state（Total /100w）: 心的状態語（動詞・形容詞・名詞）の合計 / 100語

### 解析ロジック（要点）
- 対象: CHI のみ。100番台（英語）のみ採用。**偶数=ASD / 奇数=TYP**。
- 被験者内に複数 .cha がある場合は **被験者内平均 → 群平均**（等重み）。
- BN2015 再現の 11/11 subject へ **`--restrict_to_dyads`** で合わせる。

## メタ解析CSV（`data/processed/pragmatics_meta.csv`）
- 各指標ごとに **mean/sd/n（ASD/TYP）** と **Hedges’ g, 95%CI** を出力。
- 例（ヘッダ）:  
  `metric,mean_ASD,sd_ASD,n_ASD,mean_TYP,sd_TYP,n_TYP,hedges_g,se,ci95_lo,ci95_hi`

### 出典・クレジット

- Bang, J. Y., & Nadig, A. (2015). Maternal input …（英語コーパス／T2再現のベース）
  - TalkBank Nadig corpus: <https://talkbank.org/asd/access/English/Nadig.html>

- **レビュー論文（3本）** — 本ダッシュボードの語用論指標は、これらの総説の要約に基づいて決定。
  1. **Schaeffer, J., Abd El-Raziq, M., Castroviejo, E., et al. (2023).** Language in autism: domains, profiles and co-occurring conditions. *Journal of Neural Transmission*, 130, 433–457.  
     DOI: <https://doi.org/10.1007/s00702-023-02592-y>  

  2. **Alasmari, M., Alduais, A., & Qasem, F. (2024).** Language competency in autism: a scientometric review. *Frontiers in Psychiatry*, 15:1338776.  
     DOI: <https://doi.org/10.3389/fpsyt.2024.1338776>  

  3. **Vogindroukas, I., Stankova, M., Chelas, E.-N., & Proedrou, A. (2022).** Language and Speech Characteristics in Autism. *Neuropsychiatric Disease and Treatment*, 18, 2367–2377.  
     DOI: <https://doi.org/10.2147/NDT.S331987>  

## ライセンス / データ取り扱い
- このリポジトリの **コードは MIT ライセンス** を想定。データは含めません。
- コーパスは各提供元のライセンスに従い、各自で取得してください。

## よくある質問（FAQ）
- **Contrast が 0 になる**: CHI では低頻度。辞書は上記の語を網羅的に検索。0 は“未検出”=実測ゼロ。
- **n_dyads が 13/25 になる**: `--restrict_to_dyads` で 11/11 に制限した CSV を再生成してからダッシュボードを作ってください。

---

### 開発メモ（ブランチ運用の提案）
- 公開用に `release/prag-dashboard-v1` ブランチを作り、**コード + docs + README** のみをコミット。
- `data/` や `out/` の生成物は追跡しない（`.gitignore` 参照）。
