
import numpy as np
import librosa

def segment_prosody(y, sr, start, end):
    s = int(start * sr); e = int(end * sr)
    s = max(0, min(s, len(y))); e = max(0, min(e, len(y)))
    if e <= s:
        return {"f0_mean": 0.0, "f0_sd": 0.0, "energy_mean": 0.0, "speech_rate": 0.0}

    # 切り出し
    yseg = y[s:e]

    # エネルギ
    rms = librosa.feature.rms(y=yseg).flatten()
    energy_mean = float(np.mean(rms)) if rms.size else 0.0

    # F0: 軽量な YIN を使う（110–800 Hz）
    try:
        f0 = librosa.yin(yseg, fmin=110.0, fmax=800.0)
        f0 = np.asarray(f0)
        f0 = f0[~np.isnan(f0)]
        f0_mean = float(f0.mean()) if f0.size else 0.0
        f0_sd   = float(f0.std())  if f0.size else 0.0
    except Exception:
        f0_mean = 0.0; f0_sd = 0.0

    # 簡易スピーチレート: onset 強度の局所ピーク数 / 秒
    env = np.abs(librosa.onset.onset_strength(y=yseg, sr=sr))
    if env.size >= 3:
        peaks = (env[1:-1] > env[:-2]) & (env[1:-1] > env[2:])
        n_peaks = int(peaks.sum())
    else:
        n_peaks = 0
    dur = max(1e-6, (e - s) / sr)
    speech_rate = float(n_peaks / dur)

    return {
        "f0_mean": f0_mean,
        "f0_sd": f0_sd,
        "energy_mean": energy_mean,
        "speech_rate": speech_rate,
    }
