# audio_mvp/diarize.py

from __future__ import annotations

import os
from typing import List, Dict

import librosa
import numpy as np

try:
    from pyannote.audio import Pipeline
except Exception:
    Pipeline = None  # pyannote.audio が無い環境でも import だけ通す


_PIPELINE = None


def _get_pipeline():
    """グローバルに 1 回だけ pyannote Pipeline をロード"""
    global _PIPELINE

    if Pipeline is None:
        print("[diarize] pyannote.audio がインストールされていないため、ダイアライズをスキップします。")
        return None

    if _PIPELINE is not None:
        return _PIPELINE

    # HF_TOKEN or HUGGINGFACE_TOKEN 環境変数を優先
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")

    if token:
        _PIPELINE = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            token=token,
        )
    else:
        # huggingface-cli login 済みなら token=True でも認証される
        _PIPELINE = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            token=True,
        )

    # デバイス設定（例: cpu / mps / cuda）
    device = os.environ.get("PYANNOTE_DEVICE")
    if device:
        try:
            import torch

            _PIPELINE.to(torch.device(device))
            print(f"[diarize] pyannote pipeline loaded on {device}")
        except Exception as e:  # noqa: BLE001
            print(f"[diarize] WARNING: failed to move pipeline to {device}: {e}")

    return _PIPELINE


def diarize_two_speakers(audio_path: str) -> List[Dict]:
    """
    入力: mp3/wav ファイルパス
    出力: [{"start": float, "end": float, "speaker": "S1|S2", "f0": float, "rms": float}, ...]
    """
    pipeline = _get_pipeline()
    if pipeline is None:
        return []

    import torch

    # ---- 1) librosa で 16kHz モノラル読み込み（pyannote 3.1/4.x の想定に合わせる）----
    y, sr = librosa.load(audio_path, sr=16000, mono=True)
    if y.ndim == 1:
        waveform = torch.from_numpy(y).unsqueeze(0)  # (1, time)
    else:
        waveform = torch.from_numpy(y)

    # ---- 2) DiarizeOutput を取得し、中の Annotation を取り出す ----
    # 4.x 系では pipeline(...) は DiarizeOutput を返し、
    # .speaker_diarization に Annotation が入っている:contentReference[oaicite:2]{index=2}
    out = pipeline({"waveform": waveform, "sample_rate": sr})
    ann = out.speaker_diarization  # <- コイツに対して itertracks する

    # ---- 3) ラベルごとの総発話時間からメイン 2 話者を決めて S1/S2 に割当 ----
    durations: Dict[str, float] = {}
    for turn, _, label in ann.itertracks(yield_label=True):
        durations[label] = durations.get(label, 0.0) + float(turn.end - turn.start)

    if not durations:
        return []

    labels_sorted = sorted(durations.items(), key=lambda kv: kv[1], reverse=True)
    main_labels = [lab for lab, _ in labels_sorted[:2]]
    if len(main_labels) == 1:
        # 念のため 1 話者しか見つからなかった場合も S1/S2 を埋める
        main_labels = [main_labels[0], main_labels[0]]

    label_to_S = {main_labels[0]: "S1", main_labels[1]: "S2"}

    # ---- 4) 各区間ごとに F0 と RMS を計算（assign_roles_by_f0_stats 用）----
    hop = int(sr * 0.02)  # 20ms
    segments: List[Dict] = []

    for turn, _, label in ann.itertracks(yield_label=True):
        if label not in label_to_S:
            continue

        s0, s1 = float(turn.start), float(turn.end)
        a = max(0, int(s0 * sr))
        b = min(len(y), int(s1 * sr))

        if b <= a:
            f0_med = 0.0
            rms_mean = 0.0
        else:
            yi = y[a:b]

            # F0 (YIN)
            try:
                f0 = librosa.yin(
                    yi,
                    fmin=110.0,
                    fmax=800.0,
                    frame_length=1024,
                    hop_length=hop,
                )
                f0 = np.nan_to_num(f0)
                f0_med = float(np.median(f0[f0 > 0])) if np.any(f0 > 0) else 0.0
            except Exception:  # noqa: BLE001
                f0_med = 0.0

            # RMS
            try:
                rms = librosa.feature.rms(
                    y=yi,
                    frame_length=1024,
                    hop_length=hop,
                ).ravel()
                rms_mean = float(np.mean(rms)) if len(rms) else 0.0
            except Exception:  # noqa: BLE001
                rms_mean = 0.0

        segments.append(
            {
                "start": s0,
                "end": s1,
                "speaker": label_to_S[label],
                "f0": f0_med,
                "rms": rms_mean,
            }
        )

    segments.sort(key=lambda d: d["start"])
    return segments
