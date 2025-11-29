#!/usr/bin/env python
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import math
import pandas as pd


SPEAKER_ROLES = ["CHI", "MOT"]

# ===== 語用論系パターン =====

# フィラー候補
FILLER_PATTERNS = [
    "えー",
    "えぇ",
    "えっと",
    "えと",
    "あの",
    "そのー",
    "その…",
    "うーん",
    "うんと",
    "まー",
    "まあ",
]

# 交渉的終助詞（交渉粒子）の簡易セット
SFP_NEGOTIATING_PATTERNS = [
    "よね",
    "かな",
    "だよね",
    "じゃない?",
    "じゃない？",
    "じゃないよね",
    "よ",
    "ね",
]

# 質問文っぽさを判定するための語尾・パターン
QUESTION_SUFFIX_PATTERNS = [
    "か",
    "かな",
    "かい",
    "かね",
    "の",
    "のかな",
]

# ギャップ計算で扱う最大ギャップ長（これより長いのは会話が切れている扱い）
MAX_GAP_SECONDS = 10.0


@dataclass
class MetricRow:
    metric_id: str
    session_id: str
    speaker_role: str
    value: float
    unit: str
    notes: str


def find_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    """候補名の中から、DataFrame に存在する最初の列名を返す"""
    for c in candidates:
        if c in df.columns:
            return c
    return None


# =============================================================================
# turns.csv ベース: BASIC_TOKENS_PER_TURN
# =============================================================================

def load_turn_level_counts(turns_path: Path) -> Dict[str, Dict[str, float]]:
    """
    turns.csv から role ごとの n_utts / n_tokens を読み取る。
    columns: role, n_utts, n_tokens, ...
    """
    df = pd.read_csv(turns_path)
    if "role" not in df.columns:
        raise ValueError(f"'role' column not found in {turns_path}")

    counts: Dict[str, Dict[str, float]] = {}
    for _, row in df.iterrows():
        role = str(row["role"])
        counts.setdefault(role, {})
        counts[role]["n_utts"] = float(row.get("n_utts", 0.0))
        counts[role]["n_tokens"] = float(row.get("n_tokens", 0.0))
    return counts


def compute_basic_tokens_per_turn(
    session_id: str, turn_counts: Dict[str, Dict[str, float]]
) -> List[MetricRow]:
    rows: List[MetricRow] = []

    # CHI / MOT
    for role in SPEAKER_ROLES:
        n_utts = turn_counts.get(role, {}).get("n_utts", 0.0)
        n_tokens = turn_counts.get(role, {}).get("n_tokens", 0.0)
        if n_utts > 0:
            value = n_tokens / n_utts
        else:
            value = float("nan")
        rows.append(
            MetricRow(
                metric_id="BASIC_TOKENS_PER_TURN",
                session_id=session_id,
                speaker_role=role,
                value=value,
                unit="tokens_per_turn",
                notes="n_tokens / n_utts from turns.csv",
            )
        )

    # BOTH = CHI + MOT 合算
    total_utts = sum(turn_counts.get(r, {}).get("n_utts", 0.0) for r in SPEAKER_ROLES)
    total_tokens = sum(
        turn_counts.get(r, {}).get("n_tokens", 0.0) for r in SPEAKER_ROLES
    )
    if total_utts > 0:
        both_value = total_tokens / total_utts
    else:
        both_value = float("nan")

    rows.append(
        MetricRow(
            metric_id="BASIC_TOKENS_PER_TURN",
            session_id=session_id,
            speaker_role="BOTH",
            value=both_value,
            unit="tokens_per_turn",
            notes="(CHI + MOT) n_tokens / n_utts from turns.csv",
        )
    )

    return rows


# =============================================================================
# segments.csv ベース: ギャップ / オーバーラップ / フィラー / 終助詞 / 質問率
# =============================================================================

def compute_segments_based_metrics(
    session_id: str,
    segments_path: Path,
    turn_counts: Dict[str, Dict[str, float]],
) -> List[MetricRow]:
    """
    segments.csv を使って
      - TT_GAP_MEAN
      - TT_OVERLAP_RATE
      - FILLER_RATE
      - SFP_NEGOTIATING_RATE
      - QUESTION_RATE
    を計算する。
    """
    rows: List[MetricRow] = []

    if not segments_path.exists():
        print(f"[WARN] segments.csv not found for session {session_id}, skipping segments-based metrics")
        return rows

    seg_df = pd.read_csv(segments_path)

    speaker_col = find_column(seg_df, ["speaker", "role", "spk"])
    start_col = find_column(seg_df, ["start", "start_sec", "start_time"])
    end_col = find_column(seg_df, ["end", "end_sec", "end_time"])
    text_col = find_column(seg_df, ["text", "utt", "transcript"])

    if not (speaker_col and start_col and end_col and text_col):
        print(
            f"[WARN] missing required columns in {segments_path.name} "
            f"for session {session_id}, skipping segments-based metrics"
        )
        return rows

    # 解析対象は CHI / MOT のみ
    seg_df = seg_df[seg_df[speaker_col].isin(SPEAKER_ROLES)].copy()
    if seg_df.empty:
        print(f"[WARN] no CHI/MOT rows in {segments_path.name} for session {session_id}")
        return rows

    # ---------------- ギャップ & オーバーラップ ----------------
    seg_df = seg_df.sort_values(by=start_col).reset_index(drop=True)

    starts = seg_df[start_col].astype(float).to_list()
    ends = seg_df[end_col].astype(float).to_list()
    speakers = seg_df[speaker_col].astype(str).to_list()

    gap_values = {role: [] for role in SPEAKER_ROLES}
    overlap_counts = {role: 0 for role in SPEAKER_ROLES}
    pair_counts = {role: 0 for role in SPEAKER_ROLES}

    for i in range(len(seg_df) - 1):
        spk_i = speakers[i]
        spk_j = speakers[i + 1]
        if spk_i == spk_j:
            continue  # 同一話者の連続は対象外

        if spk_j not in SPEAKER_ROLES or spk_i not in SPEAKER_ROLES:
            continue

        gap = float(starts[i + 1]) - float(ends[i])
        if abs(gap) > MAX_GAP_SECONDS:
            # 会話が途切れているレベルの長さは除外
            continue

        pair_counts[spk_j] += 1

        if gap < 0:
            # オーバーラップ
            overlap_counts[spk_j] += 1
            gap_val = 0.0  # ギャップ平均はポジティブな遅れのみを見る
        else:
            gap_val = gap

        gap_values[spk_j].append(gap_val)

    for role in SPEAKER_ROLES:
        vals = gap_values[role]
        if vals:
            mean_gap = float(sum(vals) / len(vals))
        else:
            mean_gap = float("nan")

        rows.append(
            MetricRow(
                metric_id="TT_GAP_MEAN",
                session_id=session_id,
                speaker_role=role,
                value=mean_gap,
                unit="sec",
                notes=f"mean max(0, gap) where next speaker={role}, |gap| <= {MAX_GAP_SECONDS}",
            )
        )

        total_pairs = pair_counts[role]
        if total_pairs > 0:
            overlap_rate = 100.0 * overlap_counts[role] / total_pairs
        else:
            overlap_rate = float("nan")

        rows.append(
            MetricRow(
                metric_id="TT_OVERLAP_RATE",
                session_id=session_id,
                speaker_role=role,
                value=overlap_rate,
                unit="percent",
                notes=f"percentage of turn transitions to {role} where gap < 0 (overlap), |gap| <= {MAX_GAP_SECONDS}",
            )
        )

    # ---------------- フィラー / 終助詞 / 質問率 ----------------
    filler_counts = {role: 0 for role in SPEAKER_ROLES}
    sfp_counts = {role: 0 for role in SPEAKER_ROLES}
    question_counts = {role: 0 for role in SPEAKER_ROLES}

    def normalize_text(text: str) -> str:
        return text.replace(" ", "").replace("\u3000", "")

    def strip_trailing_punct(t: str) -> str:
        while t and t[-1] in "。．.!！？?？…〜～、, 　":
            t = t[:-1].rstrip()
        return t

    def has_negotiating_sfp(text: str) -> bool:
        if not text:
            return False
        t = strip_trailing_punct(text.strip())
        if not t:
            return False
        for pat in SFP_NEGOTIATING_PATTERNS:
            if t.endswith(pat):
                return True
        return False

    def is_question(text: str) -> bool:
        if not text:
            return False
        t = text.strip()
        if "?" in t or "？" in t:
            return True
        t = strip_trailing_punct(t)
        if not t:
            return False
        for pat in QUESTION_SUFFIX_PATTERNS:
            if t.endswith(pat):
                return True
        return False

    for _, row in seg_df.iterrows():
        role = str(row[speaker_col])
        text = str(row[text_col]) if not pd.isna(row[text_col]) else ""
        norm_text = normalize_text(text)

        # フィラー
        for pat in FILLER_PATTERNS:
            filler_counts[role] += norm_text.count(pat)

        # 交渉終助詞
        if has_negotiating_sfp(text):
            sfp_counts[role] += 1

        # 質問率
        if is_question(text):
            question_counts[role] += 1

    # レートに変換
    for role in SPEAKER_ROLES:
        n_tokens = turn_counts.get(role, {}).get("n_tokens", 0.0)
        n_utts = turn_counts.get(role, {}).get("n_utts", 0.0)

        # FILLER_RATE
        if n_tokens > 0:
            filler_rate = 100.0 * filler_counts[role] / n_tokens
        else:
            filler_rate = float("nan")

        rows.append(
            MetricRow(
                metric_id="FILLER_RATE",
                session_id=session_id,
                speaker_role=role,
                value=filler_rate,
                unit="per_100_tokens",
                notes=f"count of filler patterns per 100 tokens; patterns={FILLER_PATTERNS}",
            )
        )

        # SFP_NEGOTIATING_RATE, QUESTION_RATE
        if n_utts > 0:
            sfp_rate = 100.0 * sfp_counts[role] / n_utts
            question_rate = 100.0 * question_counts[role] / n_utts
        else:
            sfp_rate = float("nan")
            question_rate = float("nan")

        rows.append(
            MetricRow(
                metric_id="SFP_NEGOTIATING_RATE",
                session_id=session_id,
                speaker_role=role,
                value=sfp_rate,
                unit="per_100_turns",
                notes=f"count of negotiating sentence-final particles per 100 turns; patterns={SFP_NEGOTIATING_PATTERNS}",
            )
        )

        rows.append(
            MetricRow(
                metric_id="QUESTION_RATE",
                session_id=session_id,
                speaker_role=role,
                value=question_rate,
                unit="per_100_turns",
                notes="heuristic question turns per 100 turns; detected by '?'/'？' and suffix patterns like 〜か / 〜かな / 〜の etc.",
            )
        )

    return rows


# =============================================================================
# prosody.csv ベース: SPEECH_RATE, PAUSE_RATIO, F0_SD
# =============================================================================

def compute_prosody_metrics(session_id: str, prosody_path: Path) -> List[MetricRow]:
    """
    prosody.csv から
      - SPEECH_RATE  (speech_rate)
      - PAUSE_RATIO  (pause_p95 を proxy として利用)
      - F0_SD        (f0_sd)
    を CHI / MOT ごとに平均値で計算する。
    """
    rows: List[MetricRow] = []

    if not prosody_path.exists():
        print(f"[WARN] prosody.csv not found for session {session_id}, skipping prosody-based metrics")
        return rows

    df = pd.read_csv(prosody_path)

    speaker_col = find_column(df, ["speaker", "role", "spk"])
    if not speaker_col:
        print(f"[WARN] no speaker column in {prosody_path.name} for session {session_id}")
        return rows

    # prosody.csv の実カラムに合わせた対応表
    spec = {
        "SPEECH_RATE": (
            ["speech_rate"],
            "per_sec",
            "mean speech rate from prosody.csv (column='speech_rate')",
        ),
        "PAUSE_RATIO": (
            ["pause_ratio", "pause_p95"],
            "pause_p95_unit",
            "proxy of pause ratio using pause_p95 (95th percentile of pause length)",
        ),
        "F0_SD": (
            ["f0_sd"],
            "Hz",
            "mean F0 standard deviation from prosody.csv (column='f0_sd')",
        ),
    }

    for metric_id, (candidates, unit, note_suffix) in spec.items():
        col = find_column(df, candidates)
        if not col:
            print(f"[WARN] column for {metric_id} not found in prosody.csv for session {session_id}")
            continue

        for role in SPEAKER_ROLES:
            sub = df[df[speaker_col] == role]
            if sub.empty:
                value = float("nan")
            else:
                s = sub[col].astype(float).dropna()
                value = float(s.mean()) if not s.empty else float("nan")

            rows.append(
                MetricRow(
                    metric_id=metric_id,
                    session_id=session_id,
                    speaker_role=role,
                    value=value,
                    unit=unit,
                    notes=note_suffix,
                )
            )

    return rows


# =============================================================================
# 全セッションを回して nanami_metric_results.csv を作る
# =============================================================================

def build_nanami_metric_results(nanami_root: Path, out_path: Path) -> None:
    """
    Nanami の 8セッションについて、以下の指標をまとめて計算して CSV を出力する:
      - BASIC_TOKENS_PER_TURN
      - TT_GAP_MEAN
      - TT_OVERLAP_RATE
      - FILLER_RATE
      - SFP_NEGOTIATING_RATE
      - QUESTION_RATE
      - SPEECH_RATE
      - PAUSE_RATIO
      - F0_SD
    """
    all_rows: List[MetricRow] = []

    session_dirs = [
        d for d in nanami_root.iterdir() if d.is_dir() and d.name[0].isdigit()
    ]
    session_dirs = sorted(session_dirs, key=lambda p: int(p.name))

    for session_dir in session_dirs:
        session_id = session_dir.name
        turns_path = session_dir / "turns.csv"
        segments_path = session_dir / "segments.csv"
        prosody_path = session_dir / "prosody.csv"

        if not turns_path.exists():
            print(f"[WARN] turns.csv not found for session {session_id}, skipping")
            continue

        print(f"[INFO] processing session {session_id}")

        turn_counts = load_turn_level_counts(turns_path)

        # BASIC_TOKENS_PER_TURN
        all_rows.extend(compute_basic_tokens_per_turn(session_id, turn_counts))
        # segments ベース
        all_rows.extend(
            compute_segments_based_metrics(session_id, segments_path, turn_counts)
        )
        # prosody ベース
        all_rows.extend(compute_prosody_metrics(session_id, prosody_path))

    if not all_rows:
        print("[WARN] no metrics computed, nothing to write")
        return

    out_df = pd.DataFrame(
        [
            {
                "metric_id": r.metric_id,
                "session_id": r.session_id,
                "speaker_role": r.speaker_role,
                "value": r.value,
                "unit": r.unit,
                "notes": r.notes,
            }
            for r in all_rows
        ]
    )

    out_df = out_df.sort_values(
        by=["metric_id", "session_id", "speaker_role"]
    ).reset_index(drop=True)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(out_path, index=False)
    print(f"[INFO] wrote metric results to {out_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Compute Nanami pragmatics metrics (tokens/turn, gaps, overlap, fillers, SFP, questions, prosody)."
    )
    parser.add_argument(
        "--nanami-root",
        type=Path,
        default=Path("out/audio/Nanami"),
        help="Nanami セッションディレクトリが並んでいるルートパス",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("out/audio/Nanami/nanami_metric_results.csv"),
        help="出力する指標結果 CSV のパス",
    )

    args = parser.parse_args()
    build_nanami_metric_results(args.nanami_root, args.out)


if __name__ == "__main__":
    main()
