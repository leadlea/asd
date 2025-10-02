# ASD-JP Audio MVP (mp3) — 9分窓 × Diarization × ASR × Prosody

このREADMEは、**mp3 等の音声**から最小構成で **会話・音声解析のMVP** を作るための実装方針と再現コマンドをまとめたものです。
目的は共同研究に向けて、**英語コーパスで構築した指標**（Tokens/Types/MLU、語用論）を**音声由来でも算出**できることを示し、将来の日本語ASDデータに水平展開することです。

---

## 1) アーキテクチャ（MVP）
- **入力**: `audio/*.mp3`（ステレオ/モノ、16 kHz 以上推奨）
- **前処理**: VAD（webrtcvad）→ セグメント化（0.2–0.5s パディング）
- **話者分離**: 簡易話者埋め込み + スペクトルクラスタリング（S1/S2 の2話者想定）
  - 初回は **半自動割当**: 2話者の代表サンプル波形を再生 → ユーザが **CHI/MOT** を指定
  - ヒューリスティクス: **平均F0が高い方=CHI** をデフォルト候補に提示
- **ASR**: Whisper (ja) で発話単位の文字起こし（タイムスタンプ付）
- **特徴量**:
  - **言語**: Tokens/Types/MLU（日本語は lemma 単位; 英語は既存と同様）
  - **語用論**: 質問率・談話標識・心的状態語（辞書は既存 `pragmatics_ja.py` を再利用）
  - **韻律**: F0(Hz)/エネルギー/発話速度（mora/秒 近似）/ポーズ分布/ターン間潜時
- **ウィンドウ**: `.cha` 不要。**9分相当**を会話の中央付近から自動抽出（総時間<9分なら全区間）
- **出力**: CSV 群 + HTML ダッシュボード（セッション表/記述統計/語用論/韻律・ターンテイク）

---

## 2) ディレクトリと依存関係
```
cpsy/
├─ audio/                # 解析対象 mp3 を置く
├─ audio_mvp/
│   ├─ audio_analyze.py  # メイン（下記CLI）
│   ├─ diarize.py        # VAD+簡易話者分離
│   ├─ asr_whisper.py    # Whisper ラッパ
│   ├─ prosody.py        # F0/energy/speech rate
│   ├─ pragmatics_ja.py  # 既存辞書を再利用 or import
│   └─ html_report.py    # ダッシュボード出力
└─ out/audio/
```
**Python 3.12**
```bash
pip install --upgrade pip
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install openai-whisper ffmpeg-python webrtcvad librosa pydub numpy pandas fugashi unidic-lite sudachipy sudachidict-full parselmouth pandas-stubs jinja2
# macOS: brew install ffmpeg
```

---

## 3) 使い方（最小実行）
```bash
# 1つのファイルを解析（日本語）
python audio_mvp/audio_analyze.py   --in audio/sample.mp3 --lang ja   --out out/audio/sample   --auto_assign_child_by_f0 true
```
**出力（例）**
```
out/audio/sample/
 ├─ segments.csv        # start,end,speaker,text
 ├─ turns.csv           # role, n_utts, n_tokens, n_types, mlu, mean_turn_len, turn_latency_mean
 ├─ prosody.csv         # role, f0_mean, f0_sd, energy_mean, speech_rate, pause_p95
 ├─ pragmatics.csv      # role, question_rate, dm_per_100t, mental_per_100t
 └─ report.html         # ダッシュボード（ローカル閲覧可）
```

---

## 4) 指標の整合（英語再現とのブリッジ）
- **Tokens/Types/MLU** は **9分窓**で両者一致（.cha 由来 vs 音声ASR由来）
- 日本語は **lemma** 集計・フィラー除外・子発話数の品質ゲート（>=20）を踏襲
- 韻律は **追加タブ**として可視化（群差の探索・ストーリーテリングに有効）

---

## 5) データ受領チェックリスト（初回）
- 音声: **16 kHz/16bit/mono** 推奨（ステレオ可; 解析時にmono化）
- 話者: **母子2話者**中心、重なり発話はそのまま（MVPでは重なりは除外/短縮）
- メタ: `session_id, child_id, child_age_months, session_minutes, notes`
- 取り扱い: **NDA準拠**（第三者提供/公開不可、可視化は匿名化）

---

## 6) 今後の拡張（優先順）
1. **Batch処理**: `audio/` 配下を一括 → `out/audio/summary.csv` 集約
2. **UI**: S1/S2 → CHI/MOT のGUI割当（2クリック）
3. **強制アラインメント**: 音素/モーラ単位の整合（Ja-Kiite/Julius/CTC系）
4. **Diarization強化**: pyannote 互換（HuggingFace token利用時）
5. **検定**: EN 同様に t 検定/効果量（g）を HTML に追加

---

## 7) 研究チーム共有テンプレ（1枚）
- **成果**: 「音声のみから 9分窓の母子会話指標（Tokens/Types/MLU/語用論/韻律）が自動算出できた」
- **差分**: 「英語再現パックと一致（TYP tokens=606.09 等）。論文本値の参照誤りを修正済み」
- **お願い**: 「初回は10ファイル程度の検証用音声をご提供いただければ、ダッシュボードで可視化して共有します」

---

## 8) 既知の限界
- ASR誤りが **MLU/Types** に影響（固有名詞・言い淀み）→ lemma化＆フィラー除外で緩和
- 重なり発話・遠距離録音は F0/エネルギー推定に不利 → 収録指針を別紙化予定

---

## 9) ライセンス・注意
- データは **NDA** の取り扱いに従うこと
- Whisper等のモデルは各ライセンス遵守（研究目的利用）
