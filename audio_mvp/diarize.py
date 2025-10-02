
import numpy as np, librosa, webrtcvad

def _merge_frames(frames, max_gap=0.2):
    segs=[]; cur=None
    for (st,ed,is_sp,r,e) in frames:
        if is_sp:
            if cur is None: cur=[st,ed,[r],[e]]
            elif st-cur[1] <= max_gap: cur[1]=ed; cur[2].append(r); cur[3].append(e)
            else: segs.append(cur); cur=[st,ed,[r],[e]]
    if cur is not None: segs.append(cur)
    return segs

def _segments_from_labels(frames, labels, offset):
    out=[]; cur=None
    for (st,ed,is_sp,r,e), lab in zip(frames, labels):
        if not is_sp or lab is None:
            if cur is not None: out.append(cur); cur=None
            continue
        spk = f"S{int(lab)+1}"
        if cur is None:
            cur={"start":st,"end":ed,"f0s":[e] if e>0 else [],"rms":[r],"speaker":spk}
        elif cur["speaker"]==spk and st-cur["end"]<=0.15:
            cur["end"]=ed; cur["rms"].append(r); 
            if e>0: cur["f0s"].append(e)
        else:
            out.append(cur)
            cur={"start":st,"end":ed,"f0s":[e] if e>0 else [],"rms":[r],"speaker":spk}
    if cur is not None: out.append(cur)
    for s in out:
        s["start"] += offset; s["end"] += offset
        s["rms"] = float(np.mean(s["rms"])) if s["rms"] else 0.0
        s["f0"]  = float(np.median(s["f0s"])) if s["f0s"] else 0.0
        del s["f0s"]
    return out

def diarize_two_speakers(audio_path):
    # 1) 音声ロード
    y, sr = librosa.load(audio_path, sr=None, mono=True)

    # 2) 長尺対策：中央12分だけでダイアライズ
    dur = librosa.get_duration(y=y, sr=sr)
    offset = 0.0
    if dur > 12*60:
        offset = max(0.0, dur/2 - 6*60)
        s = int(offset*sr); e = s + int(12*60*sr)
        y = y[s:e]

    # 3) F0: YIN（高速・堅牢）
    hop = int(sr*0.02)  # 20ms
    frame_length = 1024
    try:
        f0_series = librosa.yin(y, fmin=110.0, fmax=800.0,
                                frame_length=frame_length, hop_length=hop)
        f0_series = np.nan_to_num(f0_series)
    except Exception:
        f0_series = np.zeros(max(1, int(len(y)/hop)+1))

    # 4) RMS
    rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop).ravel()

    # 5) VAD（16k/20ms）
    import resampy
    y16 = librosa.resample(y, orig_sr=sr, target_sr=16000)
    sr16 = 16000
    vad = webrtcvad.Vad(2)
    frame_ms = 20
    step = int(sr16*frame_ms/1000.0)
    nbytes = 2
    pcm = np.clip(y16*32767.0, -32768, 32767).astype(np.int16).tobytes()

    frames=[]
    n_chunks = int(len(y16) / step)
    for i in range(n_chunks):
        st = i*(frame_ms/1000.0); ed = st + (frame_ms/1000.0)
        st16 = i*step; ed16 = st16 + step
        chunk = pcm[st16*nbytes:ed16*nbytes]
        try:
            is_sp = vad.is_speech(chunk, sample_rate=sr16)
        except Exception:
            is_sp = False
        k = int(round(st * sr / hop)); k = max(0, min(k, len(rms)-1))
        e = float(f0_series[k] if k < len(f0_series) else 0.0)
        frames.append((st,ed,is_sp,float(rms[k]),e))

    # 6) 通常セグメント化 → KMeans=2
    segs = _merge_frames(frames)
    feats=[]
    for st,ed,rs,es in segs:
        f0m = float(np.median([x for x in es if x>0])) if es else 0.0
        rm  = float(np.mean(rs)) if rs else 0.0
        feats.append((st,ed,rm,f0m))
    if not feats:
        return []

    X = np.array([[f[3], f[2]] for f in feats], dtype=float)  # [f0, rms]
    try:
        from sklearn.cluster import KMeans
        labels = KMeans(n_clusters=2, n_init=10, random_state=0).fit_predict(X)
    except Exception:
        labels = np.arange(len(feats)) % 2

    # 7) 片寄り検出
    uniq = np.unique(labels)
    degenerate = False
    if len(uniq) < 2:
        degenerate = True
    else:
        dur_by = []
        for lab in [0,1]:
            dur = sum(ed-st for (st,ed,_,_), lb in zip(feats, labels) if lb==lab)
            dur_by.append(dur)
        total = sum(dur_by)
        if total>0 and max(dur_by)/total >= 0.9:
            degenerate = True

    if not degenerate:
        out=[]
        for lab,(st,ed,rm,f0m) in zip(labels,feats):
            out.append({"start":float(st+offset), "end":float(ed+offset),
                        "f0":float(f0m), "rms":float(rm), "speaker":f"S{int(lab)+1}"})
        out.sort(key=lambda z: z["start"])
        # 近接同ラベル結合
        merged=[]
        for seg in out:
            if merged and seg["speaker"]==merged[-1]["speaker"] and seg["start"]-merged[-1]["end"]<=0.15:
                merged[-1]["end"]=seg["end"]
            else:
                merged.append(seg)
        return merged

    # 8) fallback：speechフレームを直接ラベリング
    sp_idx = [i for i,f in enumerate(frames) if f[2]]  # is_sp True のフレーム index
    if sp_idx:
        f0vals = np.array([frames[i][4] for i in sp_idx])  # ← 修正：f0 は frames[i][4]
        nz = f0vals[f0vals>0]
        labels_frames = [None]*len(frames)
        if nz.size >= 20 and (np.percentile(nz, 75) - np.percentile(nz, 25)) >= 30.0:
            thr = float(np.median(nz))
            for i in sp_idx:
                e = frames[i][4]
                lab = 0 if e < thr else 1
                labels_frames[i] = lab
        else:
            # F0で割れない→交互割当（長い沈黙>0.5sで話者切替）
            last_end = None; cur_lab = 0
            for i in sp_idx:
                st,ed = frames[i][0], frames[i][1]
                if last_end is None or st - last_end > 0.5:
                    cur_lab = 1 - cur_lab
                labels_frames[i] = cur_lab
                last_end = ed

        out = _segments_from_labels(frames, labels_frames, offset)
        return out

    return []
