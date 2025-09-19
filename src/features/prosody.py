#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse, os, pandas as pd, numpy as np
import parselmouth
import soundfile as sf

def extract_basic(audio_path):
    snd = parselmouth.Sound(audio_path)
    duration = snd.get_total_duration()
    pitch = snd.to_pitch()
    f0 = pitch.selected_array['frequency']
    f0 = f0[f0>0]
    f0_range = float(np.percentile(f0,95)-np.percentile(f0,5)) if len(f0)>10 else 0.0
    y, sr = sf.read(audio_path)
    frame = int(0.03*sr); hop = int(0.01*sr)
    energy = np.array([np.sum(y[i:i+frame]**2) for i in range(0, max(1,len(y)-frame), hop)])
    thr = np.percentile(energy, 20)
    pause_ratio = float((energy<thr).mean())
    secs = len(energy)*hop/sr
    speech_rate = float(((energy>=thr).sum()/max(1,secs))/5.0)  # 粗い近似
    return {"f0_range_hz":f0_range,"pause_ratio":pause_ratio,"speech_rate":speech_rate,"duration_sec":float(duration)}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio_root", required=True)
    ap.add_argument("--map_csv", required=True)  # utterances.csv
    ap.add_argument("--out_csv", required=True)
    args = ap.parse_args()
    df = pd.read_csv(args.map_csv)
    file_ids = sorted(df["file_id"].unique())
    rows = []
    for fid in file_ids:
        found = None
        for root, _, files in os.walk(args.audio_root):
            for f in files:
                if os.path.splitext(f)[0]==fid and f.lower().endswith(".wav"):
                    found = os.path.join(root,f); break
            if found: break
        if not found: continue
        try:
            feats = extract_basic(found); feats["file_id"]=fid; rows.append(feats)
        except Exception: continue
    out = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(args.out_csv), exist_ok=True)
    out.to_csv(args.out_csv, index=False)
    print(f"wrote prosody features -> {args.out_csv} (n={len(out)})")

if __name__ == "__main__":
    main()
