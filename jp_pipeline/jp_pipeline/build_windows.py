# -*- coding: utf-8 -*-
from typing import List, Optional, Tuple
from dataclasses import dataclass
from .cha_utils import Utt

@dataclass
class WindowSpec:
    has_time: bool
    start_idx: int
    end_idx: int
    start_ms: Optional[int]
    end_ms: Optional[int]

def nine_minute_window(utts: List[Utt], target_speakers: set, minutes: int=9,
                       assume_session_minutes: int=70) -> WindowSpec:
    """Pick a 9-min equivalent window over target speaker utterances.
    Preference: timestamps -> [t0, t0+9min]; else fraction of utterances.
    """
    ms = minutes*60*1000
    # gather all times for target speaker utterances
    times = [(i, u.start_ms, u.end_ms) for i, u in enumerate(utts) if u.speaker in target_speakers and u.start_ms is not None and u.end_ms is not None]
    if times:
        t0 = min(s for _, s, _ in times)
        tend = t0 + ms
        # indices inside [t0, tend]
        idxs = [i for i, s, e in times if s is not None and s >= t0 and s <= tend]
        if idxs:
            return WindowSpec(True, min(idxs), max(idxs), t0, tend)
    # fallback: utterance fraction based on assumed session length
    chi_idxs = [i for i, u in enumerate(utts) if u.speaker in target_speakers]
    if not chi_idxs:
        return WindowSpec(False, 0, -1, None, None)
    n = len(chi_idxs)
    n_take = max(1, round(n * (minutes/assume_session_minutes)))
    start = chi_idxs[0]
    end = chi_idxs[min(n_take-1, n-1)]
    return WindowSpec(False, start, end, None, None)
