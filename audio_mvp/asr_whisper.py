# audio_mvp/asr_whisper.py:
import os

# MPS で未実装オペレーションがあった場合に CPU に自動フォールバックさせるヒント
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

import torch
import whisper


def _detect_device() -> str:
    """
    利用可能なデバイスを検出する。

    優先順位:
      1. 環境変数 WHISPER_DEVICE (cpu / cuda / mps など)
      2. CUDA GPU
      3. Apple GPU (MPS)
      4. CPU
    """
    env_device = os.getenv("WHISPER_DEVICE")
    if env_device:
        print(f"[asr_whisper] WHISPER_DEVICE={env_device} を使用します")
        return env_device

    if torch.cuda.is_available():
        print("[asr_whisper] CUDA GPU が見つかりました")
        return "cuda"

    if hasattr(torch.backends, "mps") and torch.backends.mps.is_built() and torch.backends.mps.is_available():
        print("[asr_whisper] Apple GPU (MPS) が見つかりました")
        return "mps"

    print("[asr_whisper] GPU が見つからなかったため CPU を使用します")
    return "cpu"


def transcribe(audio_path: str, language: str = "ja", model_size: str = "small"):
    """
    Whisper で音声を書き起こし、audio_analyze.py から期待されている形式
    （start/end/text の dict のリスト）で返す。
    """
    device = _detect_device()
    print(f"[asr_whisper] loading Whisper model '{model_size}' on device='{device}'")

    model = None

    # --- MPS のときはまず試して、ダメなら CPU へフォールバック ---
    if device == "mps":
        try:
            model = whisper.load_model(model_size, device="mps")
            print("[asr_whisper] MPS でのモデル初期化に成功しました")
        except Exception as e:  # NotImplementedError, RuntimeError などまとめて捕まえる
            print(f"[asr_whisper] WARNING: MPS 初期化に失敗しました ({e}). CPU にフォールバックします")
            device = "cpu"

    # MPS 以外、または MPS 失敗時
    if model is None:
        model = whisper.load_model(model_size, device=device)

    # CUDA のときだけ fp16 を使う（MPS や CPU は fp32）
    use_fp16 = device == "cuda"

    result = model.transcribe(
        audio_path,
        language=language,
        verbose=False,
        fp16=use_fp16,
    )

    segs = []
    for s in result.get("segments", []):
        segs.append(
            {
                "start": float(s["start"]),
                "end": float(s["end"]),
                "text": s["text"].strip(),
            }
        )
    return segs
