import os
import sys
import argparse
from dataclasses import dataclass
from typing import List, Tuple, Dict

import numpy as np
import pandas as pd
import librosa

# ローカルモジュール
sys.path.insert(0, os.path.dirname(__file__))
from diarize import diarize_two_speakers           # noqa: E402
from asr_whisper import transcribe                 # noqa: E402
from prosody import segment_prosody                # noqa: E402
from pragmatics_ja import count_metrics, tokenize  # noqa: E402
from html_report import render_html                # noqa: E402

ROLE_CHILD = "CHI"
ROLE_MOTHER = "MOT"


@dataclass
class SegRow:
    start: float
    end: float
    speaker: str
    text: str


def _overlap_len(a0: float, a1: float, b0: float, b1: float) -> float:
    return max(0.0, min(a1, b1) - max(a0, b0))


def _norm_text_simple(t: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKC", t or "")
    return "".join(ch for ch in s if ch.isalnum())


# ---------- 役割（CHI/MOT）割当 ----------
def assign_roles_by_f0_stats(diar_segments: List[Dict], auto_assign_child_by_f0: bool = True) -> Dict[str, str]:
    """pyannote のダイアライズ結果（S1/S2）から、どちらを CHI/MOT にするか決める。"""
    s1 = [d.get("f0", 0.0) for d in diar_segments if d.get("speaker") == "S1" and float(d.get("f0", 0.0)) > 0]
    s2 = [d.get("f0", 0.0) for d in diar_segments if d.get("speaker") == "S2" and float(d.get("f0", 0.0)) > 0]
    med1 = float(np.median(s1)) if s1 else 0.0
    med2 = float(np.median(s2)) if s2 else 0.0

    if auto_assign_child_by_f0:
        # 高い方の F0 を CHI とみなす
        if med1 >= med2:
            return {"S1": ROLE_CHILD, "S2": ROLE_MOTHER}
        return {"S1": ROLE_MOTHER, "S2": ROLE_CHILD}

    # 強制的に S1=CHI, S2=MOT
    return {"S1": ROLE_CHILD, "S2": ROLE_MOTHER}


# ---------- ASR→話者（ダイアライズ使用） ----------
def assign_speaker_to_asr(
    asr: List[Dict],
    diar: List[Dict],
    role_map: Dict[str, str],
    min_overlap_ratio: float = 0.10,
    min_overlap_sec: float = 0.10,
    assign_pad: float = 0.25,
) -> Tuple[List[SegRow], List[Dict]]:
    """
    pyannote のダイアライズ区間をベースに、Whisper セグメントに話者を割り当てる。
    """
    diar_pad = [
        {
            "start": float(d["start"]) - assign_pad,
            "end": float(d["end"]) + assign_pad,
            "speaker": d["speaker"],
            "f0": float(d.get("f0", 0.0)),
            "rms": float(d.get("rms", 0.0)),
        }
        for d in diar
    ]

    rows: List[SegRow] = []
    diags: List[Dict] = []

    for seg in asr:
        s0, s1 = float(seg["start"]), float(seg["end"])
        dur = max(1e-6, s1 - s0)

        best = None
        best_ol = -1.0
        mid = 0.5 * (s0 + s1)

        for d in diar_pad:
            ol = _overlap_len(s0, s1, d["start"], d["end"])
            if ol > best_ol:
                best_ol = ol
                best = d

        ratio = (best_ol / dur) if dur > 0 else 0.0
        ok = (best is not None) and (ratio >= min_overlap_ratio or best_ol >= min_overlap_sec)

        # 安全網：重なりが小さくても、もっとも近い区間に必ず割当てる
        if not ok and diar_pad:
            best = min(diar_pad, key=lambda d: abs(mid - 0.5 * (d["start"] + d["end"])))
            best_ol = _overlap_len(s0, s1, best["start"], best["end"])
            ratio = (best_ol / dur) if dur > 0 else 0.0

        speaker = role_map.get(best["speaker"], "UNK") if best else "UNK"

        rows.append(
            SegRow(
                start=s0,
                end=s1,
                speaker=speaker,
                text=(seg.get("text") or "").strip(),
            )
        )
        diags.append(
            {
                "start": s0,
                "end": s1,
                "text": seg.get("text", ""),
                "assigned": speaker,
                "overlap_ratio": ratio,
                "overlap_sec": best_ol,
            }
        )

    # 隣接同話者のマージ
    rows.sort(key=lambda r: r.start)
    merged: List[SegRow] = []
    for r in rows:
        if merged and r.speaker == merged[-1].speaker and (r.start - merged[-1].end) <= 0.15:
            merged[-1] = SegRow(
                start=merged[-1].start,
                end=max(merged[-1].end, r.end),
                speaker=r.speaker,
                text=(merged[-1].text + " " + r.text).strip(),
            )
        else:
            merged.append(r)

    return merged, diags


# ---------- ASRのみ（F0クラスタ） ----------
def assign_by_f0(audio_path: str, asr_segments: List[Dict]) -> List[SegRow]:
    """
    旧ロジック：pyannote を使わず、ASR セグメント単位で F0+RMS をクラスタリングして CHI/MOT を分ける。
    """
    y, sr = librosa.load(audio_path, sr=None, mono=True)
    hop = int(sr * 0.02)  # 20ms

    feats = []  # (idx, f0_med, rms_mean)
    bounds = []  # (s0, s1)

    for i, seg in enumerate(asr_segments):
        s0, s1 = float(seg["start"]), float(seg["end"])
        a, b = max(0, int(s0 * sr)), min(len(y), int(s1 * sr))
        if b - a <= 0:
            feats.append((i, 0.0, 0.0))
            bounds.append((s0, s1))
            continue

        yi = y[a:b]

        # F0 (YIN)
        try:
            f0 = librosa.yin(yi, fmin=110.0, fmax=800.0, frame_length=1024, hop_length=hop)
            f0 = np.nan_to_num(f0)
            f0_med = float(np.median(f0[f0 > 0])) if np.any(f0 > 0) else 0.0
        except Exception:
            f0_med = 0.0

        # RMS
        try:
            rms = librosa.feature.rms(y=yi, frame_length=1024, hop_length=hop).ravel()
            rms_mean = float(np.mean(rms)) if len(rms) else 0.0
        except Exception:
            rms_mean = 0.0

        feats.append((i, f0_med, rms_mean))
        bounds.append((s0, s1))

    X = np.array([[f[1], f[2]] for f in feats], dtype=float)

    try:
        from sklearn.cluster import KMeans

        labels = KMeans(n_clusters=2, n_init=10, random_state=0).fit_predict(X)
    except Exception:
        thr = float(np.median(X[:, 0])) if len(X) else 0.0
        labels = np.array([0 if x[0] < thr else 1 for x in X], dtype=int)

    # 高F0クラスタを CHI に
    f0_means = [
        np.mean([f[1] for f, l in zip(feats, labels) if l == k]) if np.any(labels == k) else 0.0 for k in [0, 1]
    ]
    hi = int(np.argmax(f0_means))
    lo = 1 - hi  # noqa: F841  # 将来的に使うかもしれないので一応残す

    rows: List[SegRow] = []
    for (i, _f0, _rms), lab in zip(feats, labels):
        speaker = ROLE_CHILD if lab == hi else ROLE_MOTHER
        s0, s1 = bounds[i]
        text = (asr_segments[i].get("text") or "").strip()
        rows.append(SegRow(start=s0, end=s1, speaker=speaker, text=text))

    rows.sort(key=lambda r: r.start)
    merged: List[SegRow] = []
    for r in rows:
        if merged and r.speaker == merged[-1].speaker and (r.start - merged[-1].end) <= 0.15:
            merged[-1] = SegRow(
                start=merged[-1].start,
                end=max(merged[-1].end, r.end),
                speaker=r.speaker,
                text=(merged[-1].text + " " + r.text).strip(),
            )
        else:
            merged.append(r)

    return merged


# ---------- 重複・復唱の折り畳み ----------
def collapse_echo_pairs(
    rows: List[SegRow],
    max_gap: float = 0.6,
    max_chars: int = 12,
    sim_th: float = 0.92,
):
    """隣接する 2 発話が短いほぼ同一表現のとき、復唱とみなして 1 つにまとめる。"""
    from difflib import SequenceMatcher

    out: List[SegRow] = []
    echoes: List[Dict] = []
    rows = list(rows or [])
    i = 0

    while i < len(rows):
        r = rows[i]
        if i + 1 < len(rows):
            n = rows[i + 1]
            if r.speaker != n.speaker and (n.start - r.end) <= max_gap:
                a = _norm_text_simple(r.text)
                b = _norm_text_simple(n.text)
                if a and b and len(a) <= max_chars and len(b) <= max_chars:
                    if SequenceMatcher(None, a, b).ratio() >= sim_th:
                        merged = SegRow(
                            start=r.start,
                            end=max(r.end, n.end),
                            speaker=r.speaker,
                            text=(r.text + " " + n.text).strip(),
                        )
                        out.append(merged)
                        echoes.append(
                            {
                                "keep_role": r.speaker,
                                "drop_role": n.speaker,
                                "keep_start": r.start,
                                "keep_end": r.end,
                                "drop_start": n.start,
                                "drop_end": n.end,
                                "keep_text": r.text,
                                "drop_text": n.text,
                            }
                        )
                        i += 2
                        continue
        out.append(r)
        i += 1

    return out, echoes


def collapse_cross_speaker_near_dups(
    rows: List[SegRow],
    max_gap: float = 1.0,
    max_chars: int = 14,
    sim_th: float = 0.90,
    lookahead: int = 4,
):
    """
    少し離れた位置にある cross-speaker の near-duplicate をまとめる。
    """
    from difflib import SequenceMatcher

    rows = list(rows or [])
    rows.sort(key=lambda r: r.start)
    drop = set()
    dups: List[Dict] = []

    for i in range(len(rows)):
        if i in drop:
            continue
        a = rows[i]
        ta = _norm_text_simple(a.text)
        if not ta or len(ta) > max_chars:
            continue

        for j in range(i + 1, min(i + 1 + lookahead, len(rows))):
            if j in drop:
                continue
            b = rows[j]
            if b.start - a.end > max_gap:
                break
            if a.speaker == b.speaker:
                continue
            tb = _norm_text_simple(b.text)
            if not tb or len(tb) > max_chars:
                continue
            if SequenceMatcher(None, ta, tb).ratio() >= sim_th:
                # a を残し、b を drop
                rows[i] = SegRow(
                    start=a.start,
                    end=max(a.end, b.end),
                    speaker=a.speaker,
                    text=a.text,
                )
                dups.append(
                    {
                        "keep_role": a.speaker,
                        "drop_role": b.speaker,
                        "keep_start": a.start,
                        "keep_end": a.end,
                        "drop_start": b.start,
                        "drop_end": b.end,
                        "keep_text": a.text,
                        "drop_text": b.text,
                    }
                )
                drop.add(j)

    new_rows = [r for k, r in enumerate(rows) if k not in drop]
    return new_rows, dups


def clip_rows(rows: List[SegRow], w0: float, w1: float) -> List[SegRow]:
    """指定した時間窓 [w0, w1] にクリップ。"""
    out: List[SegRow] = []
    for r in rows or []:
        ns, ne = max(r.start, w0), min(r.end, w1)
        if ne > ns:
            out.append(SegRow(start=ns, end=ne, speaker=r.speaker, text=r.text))
    return out


# ---------- 集計 ----------
def make_turns(rows: List[SegRow], role: str) -> Dict:
    utts = [r for r in rows if r.speaker == role]
    n_utts = len(utts)

    toks = []
    for u in utts:
        if u.text:
            toks.extend(tokenize(u.text))

    n_tokens = len(toks)
    n_types = len({t["lemma"] for t in toks}) if toks else 0
    mlu = (n_tokens / max(1, n_utts)) if n_utts else 0.0

    lens = [(u.end - u.start) for u in utts]
    mean_turn_len = float(np.mean(lens)) if lens else 0.0

    gaps = []
    for i in range(1, len(rows)):
        A, B = rows[i - 1], rows[i]
        if A.speaker != role and B.speaker == role:
            gaps.append(max(0.0, B.start - A.end))
    turn_latency_mean = float(np.mean(gaps)) if gaps else 0.0

    return {
        "role": role,
        "n_utts": n_utts,
        "n_tokens": n_tokens,
        "n_types": n_types,
        "mlu": mlu,
        "mean_turn_len": mean_turn_len,
        "turn_latency_mean": turn_latency_mean,
    }


def make_pragmatics(rows: List[SegRow], role: str) -> Dict:
    texts = [r.text for r in rows if r.speaker == role and r.text]
    m = count_metrics(texts)
    if not m:
        m = {
            "n_utts": 0,
            "n_tokens": 0,
            "n_types": 0,
            "mlu": 0.0,
            "question_rate": 0.0,
            "dm_per_100t": 0.0,
            "mental_per_100t": 0.0,
        }
    m["role"] = role
    return m


def make_prosody(audio_path: str, rows: List[SegRow], role: str) -> Dict:
    y, sr = librosa.load(audio_path, sr=None, mono=True)
    segs = [(r.start, r.end) for r in rows if r.speaker == role]

    def pause_p95(role_: str) -> float:
        gaps = []
        for i in range(1, len(rows)):
            A, B = rows[i - 1], rows[i]
            if A.speaker == role_ and B.speaker == role_:
                gaps.append(max(0.0, B.start - A.end))
        return float(np.percentile(gaps, 95)) if gaps else 0.0

    if segs:
        stats = [segment_prosody(y, sr, s, e) for (s, e) in segs]
        f0_mean = float(np.mean([s["f0_mean"] for s in stats]))
        f0_sd = float(np.mean([s["f0_sd"] for s in stats]))
        energy_mean = float(np.mean([s["energy_mean"] for s in stats]))
        speech_rate = float(np.mean([s["speech_rate"] for s in stats]))
    else:
        f0_mean = f0_sd = energy_mean = speech_rate = 0.0

    return {
        "role": role,
        "f0_mean": f0_mean,
        "f0_sd": f0_sd,
        "energy_mean": energy_mean,
        "speech_rate": speech_rate,
        "pause_p95": pause_p95(role),
    }


# ---------- メイン ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="audio_in", required=True)
    ap.add_argument("--out", dest="outdir", required=True)
    ap.add_argument("--lang", default="ja")
    ap.add_argument("--model", default="tiny")
    ap.add_argument("--auto_assign_child_by_f0", default="true")
    ap.add_argument("--assign_mode", choices=["diar", "f0"], default="diar")

    # ダイアライズ割当の安定化
    ap.add_argument("--min_overlap_ratio", type=float, default=0.10)
    ap.add_argument("--min_overlap_sec", type=float, default=0.10)
    ap.add_argument("--assign_pad", type=float, default=0.25)

    # エコー（隣接）
    ap.add_argument("--echo_max_gap", type=float, default=0.6)
    ap.add_argument("--echo_max_chars", type=int, default=12)
    ap.add_argument("--echo_sim_th", type=float, default=0.92)

    # 近傍（非隣接）
    ap.add_argument("--near_max_gap", type=float, default=1.0)
    ap.add_argument("--near_lookahead", type=int, default=4)
    ap.add_argument("--near_sim_th", type=float, default=0.90)

    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)

    # 1) ダイアライズ（診断用に保存）
    diar = diarize_two_speakers(a.audio_in) or []
    if not diar:
        # ダイアライズ失敗時は、1 話者全体区間を仮置き
        y, sr = librosa.load(a.audio_in, sr=None, mono=True)
        dur = librosa.get_duration(y=y, sr=sr)
        diar = [{"start": 0.0, "end": float(dur), "f0": 0.0, "rms": 0.0, "speaker": "S1"}]

    pd.DataFrame(diar).to_csv(os.path.join(a.outdir, "diarization.csv"), index=False)

    # 2) 役割マップ（S1/S2 → CHI/MOT）
    auto_assign = str(a.auto_assign_child_by_f0).lower() in ("1", "true", "yes")
    role_map = assign_roles_by_f0_stats(diar, auto_assign_child_by_f0=auto_assign)

    # 3) ASR
    asr = transcribe(a.audio_in, language=a.lang, model_size=a.model)

    # 4) 話者割当
    if a.assign_mode == "diar":
        rows, diag = assign_speaker_to_asr(
            asr,
            diar,
            role_map,
            min_overlap_ratio=a.min_overlap_ratio,
            min_overlap_sec=a.min_overlap_sec,
            assign_pad=a.assign_pad,
        )
        pd.DataFrame(diag).to_csv(os.path.join(a.outdir, "diagnostics.csv"), index=False)
    else:
        rows = assign_by_f0(a.audio_in, asr)
        pd.DataFrame(
            {
                "assigned": [r.speaker for r in rows],
                "overlap_ratio": [np.nan] * len(rows),
                "overlap_sec": [np.nan] * len(rows),
            }
        ).to_csv(os.path.join(a.outdir, "diagnostics.csv"), index=False)

    # 5) 重複折り畳み
    rows, echoes = collapse_echo_pairs(
        rows,
        max_gap=a.echo_max_gap,
        max_chars=a.echo_max_chars,
        sim_th=a.echo_sim_th,
    )
    pd.DataFrame(echoes).to_csv(os.path.join(a.outdir, "echoes.csv"), index=False)

    rows, dups = collapse_cross_speaker_near_dups(
        rows,
        max_gap=a.near_max_gap,
        sim_th=a.near_sim_th,
        lookahead=a.near_lookahead,
    )
    pd.DataFrame(dups).to_csv(os.path.join(a.outdir, "duplicates.csv"), index=False)

    # 6) クリップは一旦オフ（全区間を使う）
    if rows:
        total_start, total_end = rows[0].start, rows[-1].end
        total_dur = total_end - total_start
        print(
            f"[window] using FULL duration: {total_dur:.1f} sec "
            f"({total_start:.1f}–{total_end:.1f}) without clipping"
        )

    # 7) CSV出力
    with open(os.path.join(a.outdir, "segments.csv"), "w", newline="") as f:
        import csv

        w = csv.writer(f)
        w.writerow(["start", "end", "speaker", "text"])
        for r in rows:
            w.writerow([f"{r.start:.2f}", f"{r.end:.2f}", r.speaker, r.text])

    turns = [make_turns(rows, ROLE_CHILD), make_turns(rows, ROLE_MOTHER)]
    pd.DataFrame(turns).to_csv(os.path.join(a.outdir, "turns.csv"), index=False)

    prag = [make_pragmatics(rows, ROLE_CHILD), make_pragmatics(rows, ROLE_MOTHER)]
    pd.DataFrame(prag).to_csv(os.path.join(a.outdir, "pragmatics.csv"), index=False)

    pros = [make_prosody(a.audio_in, rows, ROLE_CHILD), make_prosody(a.audio_in, rows, ROLE_MOTHER)]
    pd.DataFrame(pros).to_csv(os.path.join(a.outdir, "prosody.csv"), index=False)

    # 8) HTML
    class RowObj:
        def __init__(self, d):
            self.__dict__.update(d)

    seg_objs = [RowObj({"start": r.start, "end": r.end, "speaker": r.speaker, "text": r.text}) for r in rows]
    turn_objs = [RowObj(x) for x in turns]
    pros_objs = [RowObj(x) for x in pros]
    prag_objs = [RowObj(x) for x in prag]

    html = render_html(
        title=f"Audio MVP — {os.path.basename(a.audio_in)}",
        segments=seg_objs,
        turns=turn_objs,
        prosody=pros_objs,
        pragmatics=prag_objs,
    )

    with open(os.path.join(a.outdir, "report.html"), "w") as f:
        f.write(html)

    print(f"Done. Wrote to {a.outdir}")


if __name__ == "__main__":
    main()
