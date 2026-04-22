# Apache Parquet ガイド — S3 上の研究データを安全に扱う

更新日: 2026-04-23
対象: S3 + KMS 暗号化環境で Parquet を扱う研究者・エンジニア向け

---

## 1. Parquet とは

Apache Parquet は**列指向（columnar）**のバイナリファイル形式。
もともと Hadoop エコシステムから生まれたが、今はデータ分析の事実上の標準フォーマットになっている。

CSV が「行ごと」にデータを並べるのに対し、Parquet は「列ごと」にまとめて格納する：

```
CSV（行指向）:
  conversation_id, speaker_id, text, resp_is_aizuchi
  C001_001, IC01, こんにちは, false
  C001_001, IC02, うん, true
  ...

Parquet（列指向）:
  [conversation_id]: C001_001, C001_001, ...
  [speaker_id]:      IC01, IC02, ...
  [text]:            こんにちは, うん, ...
  [resp_is_aizuchi]: false, true, ...
```

この構造のおかげで、特定の列だけ読むときに不要な列をスキップできる。
37.8万行のテーブルから `resp_is_aizuchi` だけ集計したい場合、CSV なら全行全列を読むが、Parquet ならその1列分だけ読めばいい。

---

## 2. なぜ Parquet を採用するのか（CSV との比較）

### 2.1 型情報が保存される（再現性）

CSV は全部文字列なので、読み込むたびに型推論が揺れる（`True` が文字列になったり、数値が丸められたり）。
Parquet はスキーマ（列名・型）をファイル自体に埋め込むので、誰がいつ読んでも同じ型で復元される。
論文の再現性にとって重要。

### 2.2 SHA-256 でデータ固定できる

Parquet は**バイナリが決定的**なので SHA-256 ハッシュでバージョン固定できる。
CSV だと改行コードや引用符の揺れでハッシュが変わりやすい。

### 2.3 S3 + Athena / pandas との相性

S3 に置いた Parquet は Athena で直接 SQL クエリできる。
CSV だと型定義が面倒で、文字列のエスケープ問題も起きる。
pandas の `read_parquet()` も CSV より高速で型安全。

### 2.4 圧縮効率（コスト）

同じデータの場合：
- Parquet: 16.2 MB
- CSV: 推定 40〜60 MB

列ごとに同じ型のデータが並ぶので、Snappy / ZSTD 等の圧縮が効きやすい。
S3 の保管コストも Athena のスキャンコストも小さくなる。

### 2.5 KMS 暗号化との共存

S3 の SSE-KMS 暗号化と組み合わせても、Athena / pandas / pyarrow がシームレスに復号して読める。

### 2.6 CSV と比べた弱点

- 人間が直接テキストエディタで中身を見られない（バイナリなので）
- Excel で直接開けない（変換が必要）
- 小さいテーブルは CSV のほうが手軽（summary 等は CSV 併用が実用的）

---

## 3. Parquet を開く方法

### 3.1 方法A: aws s3 cp → pandas（最も確実）

```bash
# S3 からローカルにコピー
aws s3 cp \
  "s3://YOUR-BUCKET/gold/v13/corpus=cejc/table=pairs/part-00000.parquet" \
  /tmp/pairs.parquet

# Python で中身確認
python -c "
import pandas as pd
df = pd.read_parquet('/tmp/pairs.parquet')
print('shape:', df.shape)
print('columns:', list(df.columns))
print(df.head(3))
print(df.dtypes)
"
```

### 3.2 方法B: Python から S3 を直接読む（ダウンロード不要）

```bash
pip install s3fs  # 初回のみ
```

```python
import pandas as pd

df = pd.read_parquet(
    "s3://YOUR-BUCKET/gold/v13/corpus=cejc/table=pairs/part-00000.parquet",
    storage_options={"region_name": "ap-northeast-1"}
)
print(df.shape)
print(df.head())
```

KMS 復号は boto3 が自動で行う。一時ファイルが残らないので、コーパス管理の観点でも安全。

### 3.3 方法C: Athena で SQL クエリ（S3 上で直接）

後述のセクション4を参照。

### 3.4 方法D: VS Code 拡張（GUI プレビュー）

```
ext install dvirtz.parquet-viewer
```

インストール後、.parquet ファイルをクリックするだけでテーブル表示される。

---

## 4. Athena で S3 上の Parquet を直接クエリする

### 4.1 初期設定（初回のみ）

AWS コンソールで Athena を開き（リージョン: ap-northeast-1）、クエリ結果の保存先を設定：

「設定」→「クエリ結果の場所を管理する」→ 以下を入力：

```
s3://YOUR-BUCKET/athena-results/
```

### 4.2 データベースを作る

```sql
CREATE DATABASE IF NOT EXISTS asd_gold;
```

### 4.3 テーブルを定義する（pairs の例）

```sql
CREATE EXTERNAL TABLE asd_gold.cejc_pairs (
  conversation_id   STRING,
  prev_utt_index    BIGINT,
  prev_speaker_id   STRING,
  prev_text         STRING,
  prev_sfp_group    STRING,
  resp_utt_index    BIGINT,
  resp_speaker_id   STRING,
  resp_text         STRING,
  resp_first_token  STRING,
  resp_is_aizuchi   BOOLEAN,
  resp_is_question  BOOLEAN
)
STORED AS PARQUET
LOCATION 's3://YOUR-BUCKET/gold/v13/corpus=cejc/table=pairs/';
```

### 4.4 サンプルクエリ

```sql
-- 先頭10行を確認
SELECT * FROM asd_gold.cejc_pairs LIMIT 10;

-- 行数カウント
SELECT COUNT(*) AS total_pairs FROM asd_gold.cejc_pairs;

-- 相槌の割合
SELECT
  resp_is_aizuchi,
  COUNT(*) AS cnt,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS pct
FROM asd_gold.cejc_pairs
GROUP BY resp_is_aizuchi;

-- 会話ごとの相槌率
SELECT
  conversation_id,
  COUNT(*) AS n_pairs,
  SUM(CASE WHEN resp_is_aizuchi THEN 1 ELSE 0 END) AS n_aizuchi,
  ROUND(AVG(CASE WHEN resp_is_aizuchi THEN 1.0 ELSE 0.0 END), 4) AS aizuchi_rate
FROM asd_gold.cejc_pairs
GROUP BY conversation_id
ORDER BY aizuchi_rate DESC
LIMIT 20;

-- 特定の会話IDだけ見る
SELECT * FROM asd_gold.cejc_pairs
WHERE conversation_id = 'C001_001'
LIMIT 50;
```

### 4.5 他のテーブルも追加する場合

```sql
-- utterances（curated v1）
CREATE EXTERNAL TABLE asd_gold.cejc_utterances (
  conversation_id  STRING,
  utt_index        BIGINT,
  speaker_id       STRING,
  text             STRING,
  start_time       DOUBLE,
  end_time         DOUBLE
)
STORED AS PARQUET
LOCATION 's3://YOUR-BUCKET/curated/v1/corpus=cejc/table=utterances/';
```

カラム名がわからないテーブルは、先に pandas で `df.dtypes` を確認してから定義すると確実。

### 4.6 Athena のコスト感

- スキャンしたデータ量に課金（$5 / TB）
- 16.2 MB の pairs を全スキャンしても **$0.0001 以下**
- SELECT する列を絞るのが最も効果的なコスト削減（列指向の恩恵）

---

## 5. S3 Select は KMS 暗号化バケットで使えない

S3 コンソールの「S3 Select を使用したクエリ」は、**SSE-KMS 暗号化されたオブジェクトに対応していない**。

エラーメッセージ：「指定されたメソッドは、このリソースでは使用できません」

S3 Select が対応するのは SSE-S3（AES256）か暗号化なしのみ。
KMS 暗号化バケットでは Athena か pandas を使う。

---

## 6. アクセス方法の比較

| 方法 | KMS対応 | JOIN/GROUP BY | セットアップ | 用途 |
|------|---------|---------------|-------------|------|
| aws s3 cp → pandas | ○ | ○（Python側） | 不要 | がっつり分析 |
| Python S3直接読み | ○ | ○（Python側） | s3fs 必要 | 一時ファイル不要で安全 |
| Athena | ○ | ○ | テーブル定義が必要 | SQL で素早く確認 |
| S3 Select | ✕（KMS不可） | ✕ | 不要 | 暗号化なしの簡易確認のみ |
| VS Code 拡張 | —（ローカル） | ✕ | 拡張インストール | GUI でさっと見る |

---

## 7. 論文に書くなら

Method セクションで一文入れる場合：

> すべての中間データおよび分析結果は Apache Parquet 形式で保存し、SHA-256 ハッシュによりデータの同一性を担保した。
