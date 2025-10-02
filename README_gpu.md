# ASD 音声MVP — EC2(GPU) 実行手順まとめ

このドキュメントは、**EC2 に SSH ログインしてからレポート生成まで**を完全再現できるようにした手順書です。  
（対象：Ubuntu + NVIDIA GPU インスタンス / Python 3.8+ / CUDA ドライバ 525 系）

---

## 0. 前提
- EC2: g4dn.xlarge(T4) または g5.xlarge(A10G)（どちらでも可）
- OS: Ubuntu 20.04 / 22.04 系
- 鍵: `~/nvidia/asd-gpu-key-XXXX.pem`（権限 400）
- プロジェクト: `~/cpsy` に配置
- 日本語音声（MiiPro/Nanami）の mp3 を使用

---

## 1. SSH ログイン
```bash
ssh -i ~/nvidia/asd-gpu-key-XXXX.pem ubuntu@<EC2_PUBLIC_IP>
# 初回のみ known_hosts の追加を「yes」
```

> **ヒント**: `~/.ssh/config` に登録しておくと `ssh asd-gpu` で接続できます。

---

## 2. 基本セットアップ（1回だけ）
```bash
sudo apt update
sudo add-apt-repository -y universe || true
sudo apt update
sudo apt install -y git ffmpeg libsndfile1 python3-venv python3-pip build-essential python3-dev

# GPU ドライバ確認（表示されればOK）
nvidia-smi
```

---

## 3. 仮想環境 & ライブラリ
CUDA 12 系ドライバ(525)では **PyTorch cu118** が安定です。

```bash
mkdir -p ~/cpsy && cd ~/cpsy
python3 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip wheel setuptools

# PyTorch (CUDA 11.8 ビルド)
pip install --index-url https://download.pytorch.org/whl/cu118 "torch==2.*"

# 依存ライブラリ（Python 3.8 互換版）
pip install numpy==1.24.4 pandas==2.0.3 librosa==0.10.1             webrtcvad==2.0.10 jinja2==3.1.4 scikit-learn==1.3.2 csvkit==2.1.0             openai-whisper resampy==0.4.3 fugashi==1.3.2 unidic-lite==1.0.8
```

GPU が有効かチェック：
```bash
python - <<'PY'
import torch
print("cuda?", torch.cuda.is_available())
if torch.cuda.is_available():
    print(torch.cuda.get_device_name(0))
PY
```

---

## 4. データ配置
### 4-1) 直接ダウンロード（簡単）
```bash
mkdir -p ~/cpsy/audio/Nanami ~/cpsy/out/audio/Nanami
cd ~/cpsy/audio/Nanami
base="https://media.talkbank.org/childes/Japanese/MiiPro/Nanami"
for f in 10129 10225 10421 10622 10928 11025 20213 20319; do
  curl -fL -o "${f}.mp3" "${base}/${f}.mp3"
done
```

### 4-2) ローカルから rsync（必要に応じて）
Mac 側のターミナルで：
```bash
KEY=~/nvidia/asd-gpu-key-XXXX.pem
REMOTE=ubuntu@<EC2_PUBLIC_IP>
rsync -av -e "ssh -i $KEY -o IdentitiesOnly=yes"   /Users/<you>/cpsy/   "$REMOTE:/home/ubuntu/cpsy/"
```

---

## 5. 実行（GPU / Whisper small / F0 クラスタ割当）
```bash
cd ~/cpsy && source .venv/bin/activate
export OMP_NUM_THREADS=4

base_in=~/cpsy/audio/Nanami
base_out=~/cpsy/out/audio/Nanami

for id in 10129 10225 10421 10622 10928 11025 20213 20319; do
  python ~/cpsy/audio_mvp/audio_analyze.py     --in  "$base_in/${id}.mp3"     --out "$base_out/${id}_gpu"     --lang ja --model small --assign_mode f0
done
```

- 出力例: `/home/ubuntu/cpsy/out/audio/Nanami/10129_gpu/`  
  `report.html / segments.csv / turns.csv / prosody.csv / pragmatics.csv / echoes.csv / duplicates.csv ...`

> **メモ**: `assign_mode=f0` はダイアライズに依存せず堅牢です。後日 `assign_mode=diar` も修正可。

---

## 6. 8本のサマリーCSVを作成（任意）
```bash
python - <<'PY'
import pandas as pd, glob, os, pathlib
base=os.path.expanduser('~/cpsy/out/audio/Nanami')
rows=[]
for d in sorted(glob.glob(os.path.join(base,'*_gpu'))):
    sid=pathlib.Path(d).name.replace('_gpu','')
    t=pd.read_csv(os.path.join(d,'turns.csv'))
    p=pd.read_csv(os.path.join(d,'prosody.csv'))
    g=pd.read_csv(os.path.join(d,'pragmatics.csv'))
    tt=t.set_index('role'); pp=p.set_index('role'); gg=g.set_index('role')
    rows.append({
        'session': sid,
        'CHI_utts': tt.loc['CHI','n_utts'], 'MOT_utts': tt.loc['MOT','n_utts'],
        'CHI_tokens': tt.loc['CHI','n_tokens'], 'MOT_tokens': tt.loc['MOT','n_tokens'],
        'CHI_mlu': tt.loc['CHI','mlu'], 'MOT_mlu': tt.loc['MOT','mlu'],
        'CHI_f0': pp.loc['CHI','f0_mean'], 'MOT_f0': pp.loc['MOT','f0_mean'],
        'CHI_q': gg.loc['CHI','question_rate'], 'MOT_q': gg.loc['MOT','question_rate'],
    })
out=pd.DataFrame(rows).sort_values('session')
out['tokens_ratio_CHI_MOT']=out['CHI_tokens']/out['MOT_tokens'].replace(0,1)
out.to_csv(os.path.join(base,'Nanami_summary.csv'), index=False)
print('wrote:', os.path.join(base,'Nanami_summary.csv'))
print(out.to_string(index=False))
PY
```

---

## 7. 受け渡し
### 7-1) Macへ回収（推奨）
Mac 側で：
```bash
KEY=~/nvidia/asd-gpu-key-XXXX.pem
REMOTE=ubuntu@<EC2_PUBLIC_IP>
REMOTE_DIR=/home/ubuntu/cpsy/out/audio/Nanami
LOCAL_DIR=/Users/<you>/cpsy/out/audio/Nanami

rsync -av -e "ssh -i $KEY -o IdentitiesOnly=yes"   "$REMOTE:$REMOTE_DIR/" "$LOCAL_DIR/"
```

### 7-2) S3へ保存
```bash
sudo apt install -y awscli
aws configure  # 初回のみ
cd ~/cpsy/out/audio && tar czf Nanami_gpu_$(date +%Y%m%d).tgz Nanami/*_gpu
aws s3 cp Nanami_gpu_$(date +%Y%m%d).tgz s3://<your-bucket>/Nanami/
# またはフォルダごと同期
# aws s3 sync ~/cpsy/out/audio/Nanami s3://<your-bucket>/Nanami
```

---

## 8. 後片付け（コスト最適化）
- **Stop**（停止）: コンソールでインスタンスを停止（EBS のみ課金継続）  
- **Terminate**（削除）: 完全削除  
- CLI 例:
```bash
# 停止
aws ec2 stop-instances --instance-ids i-xxxxxxxxxxxxxxxxx --region ap-northeast-1
# OS シャットダウンだけ（EC2はRunning扱いのまま）
sudo shutdown -h now
```

---

## トラブルシュート（ショートメモ）
- `Permission denied (publickey)` → `.pem` のパス/権限 400/ユーザー名(ubuntu or ec2-user)/Key pair 名を確認
- `Unable to locate package python3.10-venv` → `python3-venv` をインストール
- `cuda? False` → 仮想環境を有効化 or ドライバ確認（`nvidia-smi`）
- `ModuleNotFoundError: fugashi` → `pip install fugashi unidic-lite`（仮想環境内）
- Whisper が遅い/誤起こし → `--model small`（GPU）/ 将来的に `faster-whisper` へ移行

---

## バージョン固定（今回の実績値）
- torch==2.* (cu118), numpy==1.24.4, pandas==2.0.3, librosa==0.10.1, scikit-learn==1.3.2
- webrtcvad==2.0.10, jinja2==3.1.4, csvkit==2.1.0, resampy==0.4.3
- fugashi==1.3.2, unidic-lite==1.0.8
- openai-whisper==20250625

---

## チェックリスト
- [ ] `nvidia-smi` が通る
- [ ] `.venv` 有効化済み
- [ ] `python ~/cpsy/audio_mvp/audio_analyze.py ...` で `Done. Wrote to ...` が出る
- [ ] `report.html` / `segments.csv` / `turns.csv` 等が作られている
- [ ] 成果を回収 or S3 に保存
- [ ] インスタンスを **Stop** で停止
