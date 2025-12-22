# CSJ/CEJC コーパス格納庫（S3）セキュリティ設定・レギュレーション準拠メモ

作成日: 2025-12-23  
対象: CSJ / CEJC コーパスを AWS S3 を「格納庫」として保管し、解析は S3 上のデータを直接（Lambda 等）参照して行う運用

---

## 1. 対象バケット

- AWSアカウント: 982534361827
- リージョン: ap-northeast-1 (Tokyo)
- バケット:
  - `leadlea-csj-backup-982534361827-20251223-002451`
  - `leadlea-cejc-backup-982534361827-20251219`

---

## 2. 適用レギュレーション（根拠）

### CSJ 利用許諾契約
- 「無断アクセス防止のための十分なセキュリティ体制」「本件利用者以外がアクセスできない措置」「ID/パスワード等によるアクセス制限」等  
  → 第10条（話し言葉コーパスの管理）  
- 契約終了時の返却/破棄/削除、要求時の証明書面提出  
  → 第18条（契約終了時の措置）

### CEJC 利用許諾契約
- 「無断アクセス防止のための十分なセキュリティ体制」「本件利用者以外がアクセスできない措置」「ID/パスワード等によるアクセス制限」等  
  → 第10条（日常会話コーパスの管理）  
- 契約終了時の返却/破棄/削除、要求時の証明書面提出  
  → 第18条（契約終了時の措置）

### CEJC 利用ガイドライン
- ネットワーク環境（ファイルサーバ等）に複製する場合「権利を有するユーザ以外がアクセスできないよう環境整備」  
  → 「② データの管理」

---

## 3. 実装方針（S3を格納庫として運用）

- ローカルPCには恒久的に保管しない（借用マシンでの保管を避け、S3を一次保管とする）
- 解析は S3 上のデータを Lambda 等から直接参照（必要最小限の権限で実行）
- バケットは **公開禁止**、**暗号化必須**、**TLS必須** を前提にハードニング

---

## 4. 実施済みセキュリティ設定（2025-12-23 時点）

両バケット共通で以下を確認・設定済み。

### 4.1 Block Public Access（公開遮断）
- BlockPublicAcls: true  
- IgnorePublicAcls: true  
- BlockPublicPolicy: true  
- RestrictPublicBuckets: true  

→ 公開設定（意図しないパブリック公開）を抑止。

### 4.2 Object Ownership（ACL無効化）
- ObjectOwnership: `BucketOwnerEnforced`

→ ACL による公開/共有を封じ、バケットオーナーの統制下に固定。

### 4.3 Versioning（バージョニング）
- Status: `Enabled`

→ 誤削除・上書き耐性を確保（復旧性の確保）。

### 4.4 Default Encryption（サーバサイド暗号化: SSE-KMS）
- SSEAlgorithm: `aws:kms`
- KMS key ARN: `arn:aws:kms:ap-northeast-1:982534361827:key/5dc3c3b6-251c-4cbd-b1a4-40f92db8f58c`
- BucketKeyEnabled: true

→ 保管時の暗号化を標準化（キー統制を含む）。

### 4.5 Bucket Policy（TLS強制）
- `DenyInsecureTransport` を設定し、`aws:SecureTransport=false` を拒否

→ 通信経路（転送時）の暗号化を強制。

> 補足: 「SSE-KMSを必須化する PutObject 制約」等を追加している場合は、
> バケットポリシー全文を別紙（付録）として保存する。

---

## 5. 検証コマンド（監査・説明用）

以下は “設定状態を第三者に説明できる形で再現可能” な確認コマンド。

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
````

---

## 6. 運用ルール（研究運用としての遵守事項）

### 6.1 アクセス主体（Principals）の最小化

* 人が直接触る IAM ユーザ/ロールは最小限
* 解析は Lambda 実行ロールに限定（必要権限のみ）
* 追加する場合も「本件利用者の範囲」から逸脱しないこと（契約/ガイドラインに従う）

### 6.2 IAM 権限（例）

* 読み取り: `s3:GetObject`, `s3:ListBucket`
* SSE-KMS: `kms:Decrypt`（必要に応じ `kms:Encrypt`/`kms:GenerateDataKey`）

### 6.3 ローカル削除（借用マシン対応）

* S3 への格納・スモークチェック完了後、ローカルのコーパス実体は削除
* 監査用には「設定確認結果（テキスト）」と「バケットポリシー全文（JSON）」のみを保持（コーパス実体やファイル一覧は残さない）

---

## 7. 付録

### 7.1 バケットポリシー全文の保存（推奨）

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

### 7.2 追加で実施を検討できる項目（監査強化）

* CloudTrail（S3 data events）で当該バケットの Read/Write を監査ログ化
* Access Analyzer / Config で継続監視（意図しない公開やポリシー逸脱の検知）
* 重要データの保護強化が必要なら Object Lock（要件次第）
