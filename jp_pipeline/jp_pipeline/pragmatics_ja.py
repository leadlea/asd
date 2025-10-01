# -*- coding: utf-8 -*-
from dataclasses import dataclass
from typing import List, Set
import re

QUESTION_PATTERNS = [
    r"[?？]\s*$",
    r"(?:か|かな|かい|かね|の\?|の？|でしょうか)\s*$",
]

DISCOURSE_MARKERS: Set[str] = {
    "でも","だから","それで","しかし","けど","ところで","つまり","じゃあ","じゃ","さて","とにかく",
    "まあ","ていうか","それでさ","それから","ところが","一方で","要するに","結局","ちなみに",
}

MENTAL_STATE: Set[str] = {
    "思う","考える","知る","分かる","わかる","覚える","忘れる","気づく","感じる","疑う","決める","覚えてる",
    "好き","嫌い","怖い","悲しい","嬉しい","楽しい","心配","安心","欲しい","～たい","願う","期待する"
}

QUESTION_RE = [re.compile(p) for p in QUESTION_PATTERNS]

@dataclass
class PragmaticsCounts:
    n_utts: int
    n_tokens: int
    q_utts: int
    dm_hits: int
    mental_hits: int
    @property
    def q_rate(self) -> float:
        return self.q_utts / self.n_utts if self.n_utts else 0.0
    @property
    def dm_per_100t(self) -> float:
        return (self.dm_hits / self.n_tokens * 100) if self.n_tokens else 0.0
    @property
    def mental_per_100t(self) -> float:
        return (self.mental_hits / self.n_tokens * 100) if self.n_tokens else 0.0

def is_question(utt_text: str) -> bool:
    t = utt_text.strip()
    for rx in QUESTION_RE:
        if rx.search(t):
            return True
    return False

def count_hits_in_lemmas(lemmas: List[str], lex: Set[str]) -> int:
    return sum(1 for le in lemmas if le in lex)

def analyze_pragmatics(utts_text: List[str], tokenizer) -> PragmaticsCounts:
    n_utts = len(utts_text)
    n_tokens = 0; q_utts = 0; dm_hits = 0; mental_hits = 0
    for ut in utts_text:
        if is_question(ut):
            q_utts += 1
        lemmas, _ = tokenizer.tokenize_lemmas(ut)
        n_tokens += len(lemmas)
        dm_hits += count_hits_in_lemmas(lemmas, DISCOURSE_MARKERS)
        mental_hits += count_hits_in_lemmas(lemmas, MENTAL_STATE)
    return PragmaticsCounts(n_utts=n_utts, n_tokens=n_tokens, q_utts=q_utts,
                            dm_hits=dm_hits, mental_hits=mental_hits)
