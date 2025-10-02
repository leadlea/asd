# /Users/genfukuhara/cpsy/audio_mvp/diarize_fallback.py
import numpy as np, librosa

def diarize_two_speakers(audio_path):
    y, sr = librosa.load(audio_path, sr=None, mono=True)
    # 中央12分だけに短縮（長尺対策）
    dur = librosa.get_duration(y=y, sr=sr)
    if dur > 12*60:
        start = max(0.0, dur/2 - 6*60)
        s = int(start*sr); e = s + int(12*60*sr)
        y = y[s:e]

    hop = int(sr*0.02)  # 20ms
    rms = librosa.feature.rms(y=y, frame_length=hop, hop_length=hop).ravel()
    thr = np.percentile(rms, 60)  # 簡易しきい値
    segs=[]; cur=None
    for i,val in enumerate(rms):
        t0=i*hop/sr; t1=t0+0.02
        if val>=thr:
            if cur is None: cur=[t0,t1]
            elif t0-cur[1] <= 0.2: cur[1]=t1
            else: segs.append(cur); cur=[t0,t1]
    if cur is not None: segs.append(cur)

    # S1/S2 を交互に振る（簡易）
    out=[]
    for i,(t0,t1) in enumerate(segs):
        out.append({"start":float(t0),"end":float(t1),"f0":0.0,"rms":0.0,"speaker":"S1" if i%2==0 else "S2"})
    return out
