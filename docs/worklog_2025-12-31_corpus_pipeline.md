# 作業ログ（2025-12-31）CEJC/CSJ：curated→gold→analysis パイプライン整備

## 0. 目的
- CEJC / CSJ の元データ（SQLite/RDB 由来）を **S3上で Parquet 化（curated）**し、
- 発話単位の派生特徴（終助詞・疑問・相槌など）を付与した **gold データセット**を生成、
- 会話サブセット（CEJC dyad、CSJ dialog）とランキング分析（NE→相槌）まで含めて **再現可能な分析基盤**を構築する。

---

## 1. 実行環境 / 前提
- Python 3.12 + venv
- AWS CLI / boto3
- S3 への Put/Upload に KMS 暗号化を使用（SSE-KMS）
  - `S3_KMS_KEY_ARN=arn:aws:kms:ap-northeast-1:982534361827:key/5dc3c3b6-251c-4cbd-b1a4-40f92db8f58c`

---

## 2. 入力データ（S3）
### CEJC SQLite
- `s3://leadlea-cejc-backup-982534361827-20251219/CEJC/rdb/cejc.db`

### curated/gold/analysis 出力先
- curated: `s3://leadlea-asd-curated-982534361827-20251230/curated/v1`
- gold:    `s3://leadlea-asd-curated-982534361827-20251230/gold`
- analysis:`s3://leadlea-asd-curated-982534361827-20251230/analysis/v1`

---

## 3. 主要トラブルと対応
### 3.1 Parquet変換時の pyarrow 型エラー
- エラー：
  - `pyarrow.lib.ArrowTypeError: Expected bytes, got a 'int' object`
  - `Conversion failed for column housemate with type object`
- 対応方針：
  - SQLite 由来の **object列に int/bytes/str が混在**していたため、Parquet書き込み前に型を安定化（文字列化 or 適切なキャスト）する方向で回避。
- 結果：
  - curated 生成を継続でき、下記の curated 出力が完成。

---

## 4. curated（Parquet化）出力
### 4.1 CEJC curated/v1
S3（抜粋）：
- `curated/v1/corpus=cejc/table=infoConversation/part-00000.parquet`
- `curated/v1/corpus=cejc/table=infoSession/part-00000.parquet`
- `curated/v1/corpus=cejc/table=infoSessionGroup/part-00000.parquet`
- `curated/v1/corpus=cejc/table=infoParticipant/part-00000.parquet`
- `curated/v1/corpus=cejc/table=infoInformant/part-00000.parquet`
- `curated/v1/corpus=cejc/table=utterances/part-00000.parquet`

### 4.2 CSJ curated/v1
S3（抜粋）：
- `curated/v1/corpus=csj/table=infoDialog/part-00000.parquet`
- `curated/v1/corpus=csj/table=infoSpeaker/part-00000.parquet`
- `curated/v1/corpus=csj/table=infoTalk/part-00000.parquet`
- `curated/v1/corpus=csj/table=utterances/part-00000.parquet`

---

## 5. 会話マニフェスト（conversation_manifest）
### 5.1 CSJ conversation_manifest（TalkType/Genre 等も含めて集計）
- 出力：
  - `s3://leadlea-asd-curated-982534361827-20251230/curated/v1/corpus=csj/table=conversation_manifest/part-00000.parquet`
- 件数：
  - rows: 201
  - `is_dialogue=True: 18`, `False: 183`
  - TalkType と一致（dialog=18, monolog=183）

### 5.2 CEJC conversation_manifest
- 出力：
  - `s3://leadlea-asd-curated-982534361827-20251230/curated/v1/corpus=cejc/table=conversation_manifest/part-00000.parquet`
- 件数：
  - rows: 577
  - `is_dialogue=True: 577`（全件対話）

### 5.3 CEJC enriched / dyad 切り出し
- enriched（group_type付与）：
  - `s3://leadlea-asd-curated-982534361827-20251230/curated/v1/corpus=cejc/table=conversation_manifest_enriched/part-00000.parquet`
- dyad（n_speakers==2）：
  - `s3://leadlea-asd-curated-982534361827-20251230/curated/v1/corpus=cejc/table=conversation_manifest_dyad/part-00000.parquet`
- 件数：
  - cejc total 577 / dyad 224
  - group_type: dyad 224 / small_group 225 / large_group 128

---

## 6. gold データ生成（v8）
`build_pragmatics_gold_from_utterances.py` にて、終助詞グルーピング・疑問判定・応答ペア抽出・相槌判定などを実装し、複数回の改善を経て **v8** を確定。

### 6.1 CEJC gold/v8（--loose-aizuchi 使用）
- 出力：
  - `s3://leadlea-asd-curated-982534361827-20251230/gold/v8/corpus=cejc/table=segments/part-00000.parquet`
  - `s3://leadlea-asd-curated-982534361827-20251230/gold/v8/corpus=cejc/table=pairs/part-00000.parquet`
  - `s3://leadlea-asd-curated-982534361827-20251230/gold/v8/corpus=cejc/table=metrics_sfp/part-00000.parquet`
  - `s3://leadlea-asd-curated-982534361827-20251230/gold/v8/corpus=cejc/table=metrics_resp/part-00000.parquet`
- 規模：
  - segments: 577,885 / pairs: 378,350 / metrics_sfp: 2,033 / metrics_resp: 2,033
- 終助詞グループ比率（抜粋）：
  - OTHER 0.646 / NONLEX 0.2128 / NE 0.0679 / YO 0.0274 / NO 0.0214 / NA 0.0182 / …
- question_rate（疑問判定）：
  - 約 0.0689
- aizuchi rate（相槌判定）：
  - 約 0.4728
- 確認：
  - 「短いが相槌扱いされていない応答」の上位を抽出し、ルール改善に反映（v6→v8で改善）

### 6.2 CSJ gold/v8（--loose-aizuchi 使用）
- 出力：
  - `s3://leadlea-asd-curated-982534361827-20251230/gold/v8/corpus=csj/table=segments/part-00000.parquet`
  - `s3://leadlea-asd-curated-982534361827-20251230/gold/v8/corpus=csj/table=pairs/part-00000.parquet`
  - `s3://leadlea-asd-curated-982534361827-20251230/gold/v8/corpus=csj/table=metrics_sfp/part-00000.parquet`
  - `s3://leadlea-asd-curated-982534361827-20251230/gold/v8/corpus=csj/table=metrics_resp/part-00000.parquet`
- 規模：
  - segments: 66,117 / pairs: 5,142 / metrics_sfp: 219 / metrics_resp: 36
- CSJ は monolog が多く、pairs/metrics_resp は dialog 部分中心のため行数が小さめ

---

## 7. サブセット生成（v8）
### 7.1 CEJC dyad subset（224会話）
- 出力：
  - `s3://leadlea-asd-curated-982534361827-20251230/gold/v8/corpus=cejc/subset=dyad/table=segments/part-00000.parquet`
  - `s3://leadlea-asd-curated-982534361827-20251230/gold/v8/corpus=cejc/subset=dyad/table=pairs/part-00000.parquet`
  - `s3://leadlea-asd-curated-982534361827-20251230/gold/v8/corpus=cejc/subset=dyad/table=metrics_sfp/part-00000.parquet`
  - `s3://leadlea-asd-curated-982534361827-20251230/gold/v8/corpus=cejc/subset=dyad/table=metrics_resp/part-00000.parquet`
- 行数：
  - segments 160,501 / pairs 89,363 / metrics_* 448

### 7.2 CSJ dialog subset（18会話）
- 出力：
  - `s3://leadlea-asd-curated-982534361827-20251230/gold/v8/corpus=csj/subset=dialog/table=segments/part-00000.parquet`
  - `s3://leadlea-asd-curated-982534361827-20251230/gold/v8/corpus=csj/subset=dialog/table=pairs/part-00000.parquet`
  - `s3://leadlea-asd-curated-982534361827-20251230/gold/v8/corpus=csj/subset=dialog/table=metrics_sfp/part-00000.parquet`
  - `s3://leadlea-asd-curated-982534361827-20251230/gold/v8/corpus=csj/subset=dialog/table=metrics_resp/part-00000.parquet`
- 行数：
  - segments 8,315 / pairs 5,142 / metrics_sfp 36 / metrics_resp 36

---

## 8. analysis（サマリ & NE→相槌ランキング）
### 8.1 データセットサマリ
- 出力：
  - `s3://leadlea-asd-curated-982534361827-20251230/analysis/v1/gold=v8/summary/summary_datasets.parquet`
  - `s3://leadlea-asd-curated-982534361827-20251230/analysis/v1/gold=v8/summary/summary_datasets.csv`
- 対象 dataset：
  - cejc_all / cejc_dyad / csj_all / csj_dialog
- 例：preview では各 dataset の conversation数・行数・終助詞比率などを一覧化

### 8.2 NE→AIZUCHI ランキング出力（top/bottom/reliable）
- 出力（例）：
  - `analysis/v1/gold=v8/rank_ne_aizuchi/cejc_all/top50.parquet`
  - `analysis/v1/gold=v8/rank_ne_aizuchi/cejc_all/bottom50.parquet`
  - `analysis/v1/gold=v8/rank_ne_aizuchi/cejc_all/all_reliable.parquet`
  - `analysis/v1/gold=v8/rank_ne_aizuchi/cejc_dyad/top50.parquet`
  - `analysis/v1/gold=v8/rank_ne_aizuchi/cejc_dyad/bottom50.parquet`
  - `analysis/v1/gold=v8/rank_ne_aizuchi/cejc_dyad/all_reliable.parquet`
  - `analysis/v1/gold=v8/rank_ne_aizuchi/csj_all/*`
  - `analysis/v1/gold=v8/rank_ne_aizuchi/csj_dialog/*`

---

## 9. 例文抽出（ランキング上位/下位のペアを確認可能に）
CEJC dyad のランキング（top/bottom）から、pairs を引いて **NE/NE_Q 起点の応答例文**を抽出し、S3に保存。

- 出力：
  - `s3://leadlea-asd-curated-982534361827-20251230/analysis/v1/gold=v8/examples/ne_aizuchi/cejc_dyad/examples_all.csv`
  - `s3://leadlea-asd-curated-982534361827-20251230/analysis/v1/gold=v8/examples/ne_aizuchi/cejc_dyad/examples_all.parquet`
  - `.../examples_top.*`
  - `.../examples_bottom.*`
- 目的：
  - ランキング結果の「なぜ上位/下位か」を発話例で検証し、相槌判定ルール・辞書改善に繋げる。

---

## 10. 既知の警告（現状は致命的ではない）
- pandas `FutureWarning: DataFrameGroupBy.apply operated on the grouping columns...`
  - 将来の pandas で挙動が変わる可能性
  - 対策候補：`include_groups=False` を使う or groupby後に列選択してから apply する

---

## 11. 次アクション案
- (A) CEJC dyad の `examples_top/bottom` を確認し、
  - 相槌に入れたい短文（例：へー / いや / ほら / これ / なんか 等）の扱い整理
  - 相槌に入れたくない短文（例：質問・確認・反論など）の例外整理
- (B) v9 を作り、同じ手順で gold/analysis を再生成して差分比較（aizuchi_rate / rank 安定性）
- (C) CSJ は monolog が多いので、dialog subset を主として比較・報告できるよう整備

---

## 付録：主要な生成物（S3パス一覧）
### curated
- `.../curated/v1/corpus=cejc/table=utterances/part-00000.parquet`
- `.../curated/v1/corpus=csj/table=utterances/part-00000.parquet`
- `.../curated/v1/corpus=csj/table=conversation_manifest/part-00000.parquet`
- `.../curated/v1/corpus=cejc/table=conversation_manifest/part-00000.parquet`
- `.../curated/v1/corpus=cejc/table=conversation_manifest_dyad/part-00000.parquet`

### gold v8
- `.../gold/v8/corpus=cejc/table=*`
- `.../gold/v8/corpus=csj/table=*`
- `.../gold/v8/corpus=cejc/subset=dyad/table=*`
- `.../gold/v8/corpus=csj/subset=dialog/table=*`

### analysis v1 gold=v8
- `.../analysis/v1/gold=v8/summary/summary_datasets.(csv|parquet)`
- `.../analysis/v1/gold=v8/rank_ne_aizuchi/**`
- `.../analysis/v1/gold=v8/examples/ne_aizuchi/cejc_dyad/examples_*.{csv,parquet}`
