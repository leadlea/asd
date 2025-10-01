# -*- coding: utf-8 -*-
import re
from dataclasses import dataclass
from typing import Optional, Tuple, List

TIME_RE = re.compile(r"\x15(\d+)_([0-9]+)\x15")
TIER_RE = re.compile(r"^\*([A-Z]+):\s*(.*)$")

def extract_time_bounds(line: str) -> Optional[Tuple[int,int]]:
    """Return (start_ms, end_ms) if CHA inline timing exists."""
    m = TIME_RE.search(line)
    if not m:
        return None
    try:
        return int(m.group(1)), int(m.group(2))
    except Exception:
        return None

def strip_cha_markup(text: str) -> str:
    """Remove common CHA markup that shouldn't be tokenized."""
    # remove inline timing
    text = TIME_RE.sub("", text)
    # remove bracketed codes like [=!], [//], [%exp], etc.
    text = re.sub(r"\[[^\]]*\]", "", text)
    # remove comments in {} and <> (events/overlaps)
    text = re.sub(r"\{[^}]*\}", "", text)
    text = re.sub(r"\<[^>]*\>", "", text)
    # normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text

@dataclass
class Utt:
    speaker: str
    text: str
    start_ms: Optional[int]
    end_ms: Optional[int]

def iter_utterances(path: str) -> List[Utt]:
    """Read a .cha file and yield Utt objects for *-tiers only (skip dependent tiers)."""
    utts: List[Utt] = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.rstrip("\n")
            m = TIER_RE.match(line)
            if not m:
                continue
            spk, body = m.group(1), m.group(2)
            tb = extract_time_bounds(body)
            clean = strip_cha_markup(body)
            if not clean:
                continue
            utts.append(Utt(spk, clean, tb[0] if tb else None, tb[1] if tb else None))
    return utts
