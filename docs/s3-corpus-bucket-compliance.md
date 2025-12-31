# CSJ/CEJC corpus pipeline（S3格納庫 + curated(v1) → gold(v13)）作業サマリー & 再現手順

更新日: 2025-12-31  
対象: CSJ / CEJC コーパスを AWS S3 を「格納庫」として安全に保管し、S3上で **curated(v1) → gold(v13)** を生成して語用論指標（終助詞/疑問/相槌）を分析可能な状態に整備する。

---

## 1. 目的（山下先生向け要約）

- CSJ/CEJC の利用許諾・ガイドラインに沿って **第三者アクセスを防止できるS3保管体制** を整備する。  
- コーパスから **発話（utterances）→ 指標付きセグメント（segments）→ 応答ペア（pairs）→ 集計指標（metrics）** の形に変換し、研究で利用可能な「gold」データセットを作る。  
- 特に「相槌（aizuchi）」・「疑問判定（question）」・「終助詞群（SFP）」の妥当性を検証し、ルールを段階的に改善（v8→v13）した。

---

## 2. 対象バケット（格納庫）

- AWSアカウント: 982534361827
- リージョン: ap-northeast-1 (Tokyo)

### 2.1 原本保管（バックアップ）
- `leadlea-csj-backup-982534361827-20251223-002451`
- `leadlea-cejc-backup-982534361827-20251219`

### 2.2 解析用アウトプット（curated / gold / analysis）
- `leadlea-asd-curated-982534361827-20251230`
  - curated(v1): `s3://leadlea-asd-curated-982534361827-20251230/curated/v1`
  - gold: `s3://leadlea-asd-curated-982534361827-20251230/gold`
  - analysis: `s3://leadlea-asd-curated-982534361827-20251230/analysis/v1`

---

## 3. 適用レギュレーション（根拠）

### CSJ 利用許諾契約
- 無断アクセス防止、利用者以外アクセス不可、ID/パスワード等でアクセス制限  
  → 第10条（話し言葉コーパスの管理）
- 契約終了時の返却/破棄/削除、要求時の証明  
  → 第18条（契約終了時の措置）

### CEJC 利用許諾契約
- 無断アクセス防止、利用者以外アクセス不可、ID/パスワード等でアクセス制限  
  → 第10条（日常会話コーパスの管理）
- 契約終了時の返却/破棄/削除、要求時の証明  
  → 第18条（契約終了時の措置）

### CEJC 利用ガイドライン
- ネットワーク環境（ファイルサーバ等）に複製する場合、権利者以外がアクセスできない環境整備  
  → 「② データの管理」

---

## 4. S3 格納庫のセキュリティ実装（監査可能な状態）

両バケット共通で以下を確認・設定済み。

### 4.1 Block Public Access（公開遮断）
- BlockPublicAcls: true  
- IgnorePublicAcls: true  
- BlockPublicPolicy: true  
- RestrictPublicBuckets: true  

→ 意図しない公開設定を抑止。

### 4.2 Object Ownership（ACL無効化）
- ObjectOwnership: `BucketOwnerEnforced`

→ ACL による共有/公開を封じ、統制下に固定。

### 4.3 Versioning（バージョニング）
- Status: `Enabled`

→ 誤削除・上書き耐性を確保。

### 4.4 Default Encryption（SSE-KMS）
- SSEAlgorithm: `aws:kms`
- KMS key ARN: `arn:aws:kms:ap-northeast-1:982534361827:key/5dc3c3b6-251c-4cbd-b1a4-40f92db8f58c`
- BucketKeyEnabled: true

→ 保管時の暗号化を標準化。

### 4.5 Bucket Policy（TLS強制）
- `aws:SecureTransport=false` を拒否（DenyInsecureTransport）

→ 転送時暗号化を強制。

---

## 5. パイプライン成果（curated(v1) → gold(v13)）

### 5.1 gold の出力テーブル
各 corpus ごとに、以下4テーブルを S3 に生成。

- segments: 発話に SFP（終助詞群）と疑問フラグを付与
- pairs: 話者交替時のみ prev→resp の応答ペアを生成（resp側に相槌フラグ等）
- metrics_sfp: 会話×話者単位で SFP/疑問の比率などを集計
- metrics_resp: 会話×話者単位で「NE後の相槌率」や「応答語彙エントロピー」などを集計

出力先（例: v13）  
- `s3://leadlea-asd-curated-982534361827-20251230/gold/v13/corpus=cejc/table=...`
- `s3://leadlea-asd-curated-982534361827-20251230/gold/v13/corpus=csj/table=...`

### 5.2 妥当性検証とルール改善（v8 → v13）
相槌の取りこぼし（短応答なのに non-aizuchi）を中心に検証し、段階的にルールを更新。

- v8: 初期 gold 生成（CEJC/CSJ ともに生成可能。CSJはタグ混在の影響あり）
- v9〜v11: CSJタグ（<H>/<FV>/<息> 等）や括弧注記の正規化、相槌検出の頑健化
- v12: 「うんー」等の **長音（ー）を含む相槌** を拾えるよう改善（CEJCで改善が観測）
- v13: 同意系の相槌（**ですよね/だよね/まあね/まぁね**）を追加（微増で副作用小）

#### 実測（今回ログ）
- CSJ aizuchi rate:  
  - v12: 0.38156 → v13: 0.38254（微増、暴走なし）
- CEJC aizuchi rate:  
  - v12: 0.50997 → v13: 0.51114（改善が観測）

---

## 6. 運用ルール（研究運用としての遵守事項）

### 6.1 アクセス主体（Principals）の最小化
- 人が直接触る IAM ユーザ/ロールは最小限
- 解析は Lambda 等の実行ロールに限定（必要権限のみ）
- 追加する場合も「本件利用者の範囲」から逸脱しない（契約/ガイドライン順守）

### 6.2 IAM 権限（例）
- 読み取り: `s3:GetObject`, `s3:ListBucket`
- SSE-KMS: `kms:Decrypt`（必要に応じ `kms:Encrypt`/`kms:GenerateDataKey`）

### 6.3 ローカル削除（借用マシン対応）
- S3 への格納・スモークチェック完了後、ローカルのコーパス実体は削除
- 監査用には「設定確認結果（テキスト）」と「バケットポリシー全文（JSON）」のみ保持  
  （コーパス実体やファイル一覧は残さない）

---

## 7. 再現性（環境変数・検証コマンド・最終コマンド）

### 7.1 必須 env（解析出力先）
```bash
export S3_KMS_KEY_ARN="arn:aws:kms:ap-northeast-1:982534361827:key/5dc3c3b6-251c-4cbd-b1a4-40f92db8f58c"
export OUT_CURATED="s3://leadlea-asd-curated-982534361827-20251230/curated/v1"
export OUT_GOLD="s3://leadlea-asd-curated-982534361827-20251230/gold"
export ANALYSIS_OUT="s3://leadlea-asd-curated-982534361827-20251230/analysis/v1"
````

（任意）envファイル化

```bash
cat > env_asd.sh <<'SH'
export S3_KMS_KEY_ARN="arn:aws:kms:ap-northeast-1:982534361827:key/5dc3c3b6-251c-4cbd-b1a4-40f92db8f58c"
export OUT_CURATED="s3://leadlea-asd-curated-982534361827-20251230/curated/v1"
export OUT_GOLD="s3://leadlea-asd-curated-982534361827-20251230/gold"
export ANALYSIS_OUT="s3://leadlea-asd-curated-982534361827-20251230/analysis/v1"
SH
source env_asd.sh
```

### 7.2 S3セキュリティ設定の監査コマンド（第三者説明用）

```bash
REGION="ap-northeast-1"
BUCKETS=(
  "leadlea-csj-backup-982534361827-20251223-002451"
  "leadlea-cejc-backup-982534361827-20251219"
)

for B in "${BUCKETS[@]}"; do
  echo "===== $B ====="
  aws s3api get-public-access-block --bucket "$B" --region "$REGION"
  aws s3api get-bucket-ownership-controls --bucket "$B" --region "$REGION"
  aws s3api get-bucket-versioning --bucket "$B" --region "$REGION"
  aws s3api get-bucket-encryption --bucket "$B" --region "$REGION"
  aws s3api get-bucket-policy --bucket "$B" --region "$REGION" --query Policy --output text | head -c 500; echo " ..."
done
```

### 7.3 gold(v13) 生成（最終コマンド：再現性担保）

```bash
# CSJ v13
python scripts/build_pragmatics_gold_from_utterances.py \
  --corpus csj \
  --utterances-s3 "$OUT_CURATED/corpus=csj/table=utterances/part-00000.parquet" \
  --out-s3-prefix "$OUT_GOLD" \
  --out-version 13 \
  --loose-aizuchi

# CEJC v13
python scripts/build_pragmatics_gold_from_utterances.py \
  --corpus cejc \
  --utterances-s3 "$OUT_CURATED/corpus=cejc/table=utterances/part-00000.parquet" \
  --out-s3-prefix "$OUT_GOLD" \
  --out-version 13 \
  --loose-aizuchi
```

---

## 8. 付録（推奨）

### 8.1 バケットポリシー全文の保存（推奨）

```bash
REGION="ap-northeast-1"
mkdir -p security_artifacts

for B in \
  "leadlea-csj-backup-982534361827-20251223-002451" \
  "leadlea-cejc-backup-982534361827-20251219"; do
  aws s3api get-bucket-policy --bucket "$B" --region "$REGION" \
    --query Policy --output text > "security_artifacts/${B}_bucket-policy.json"
done
```

### 8.2 追加で実施を検討できる項目（監査強化）

* CloudTrail（S3 data events）で当該バケット Read/Write を監査ログ化
* Access Analyzer / Config で継続監視（意図しない公開やポリシー逸脱の検知）
* 重要度が高ければ Object Lock（要件次第）