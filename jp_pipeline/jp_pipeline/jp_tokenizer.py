# -*- coding: utf-8 -*-
from dataclasses import dataclass
from typing import List, Tuple, Optional, Set

# Primary: fugashi (UniDic short unit words). Fallback: SudachiPy dict_full mode C.
@dataclass
class Tokenization:
    surface: str
    lemma: str
    is_oov: bool = False

class JapaneseTokenizer:
    def __init__(self, filler_set: Optional[Set[str]]=None):
        self.filler_set = filler_set or set()
        # Lazy init libs to keep import errors readable
        self._fugashi = None
        self._sudachi = None
        self._sudachi_mode = None

    def _init_fugashi(self):
        if self._fugashi is None:
            from fugashi import Tagger
            self._fugashi = Tagger()  # uses installed UniDic (recommend: unidic-lite for portability)

    def _init_sudachi(self):
        if self._sudachi is None:
            from sudachipy import dictionary, tokenizer
            self._sudachi = dictionary.Dictionary(dict="full").create()
            self._sudachi_mode = tokenizer.Tokenizer.SplitMode.C

    def _fugashi_tokens(self, text: str) -> List[Tokenization]:
        self._init_fugashi()
        out: List[Tokenization] = []
        for w in self._fugashi(text):
            # attempt robust lemma access across fugashi/unidic versions
            lemma = None
            try:
                lemma = getattr(w, "lemma", None)
            except Exception:
                lemma = None
            if not lemma:
                try:
                    feat = getattr(w, "feature", None)
                    if feat:
                        lemma = getattr(feat, "lemma", None) or getattr(feat, "dictionary_form", None)
                except Exception:
                    lemma = None
            if not lemma:
                lemma = w.surface
            out.append(Tokenization(surface=w.surface, lemma=lemma, is_oov=False))
        return out

    def _sudachi_tokens(self, text: str) -> List[Tokenization]:
        self._init_sudachi()
        toks = self._sudachi.tokenize(text, self._sudachi_mode)
        out: List[Tokenization] = []
        for t in toks:
            lemma = t.normalized_form()  # robust lemma/normalized form
            out.append(Tokenization(surface=t.surface(), lemma=lemma, is_oov=False))
        return out

    def tokenize_lemmas(self, text: str) -> Tuple[List[str], List[str]]:
        """
        Returns (lemmas_excluding_fillers, filler_hits)
        - primary: fugashi; if empty or obviously broken, fallback to sudachi
        - fillers compared on surface and lemma (exact match); can extend upstream by reading a lexicon
        """
        prim = self._fugashi_tokens(text)
        toks = prim
        if not toks:
            toks = self._sudachi_tokens(text)

        lemmas: List[str] = []
        filler_hits: List[str] = []
        for tk in toks:
            surf = tk.surface.strip()
            lem = tk.lemma.strip()
            if not surf:
                continue
            # treat ASCII punctuation and bare symbols as non-words
            if all(ord(c) < 128 and not c.isalnum() for c in surf):
                continue
            # filter fillers
            if surf in self.filler_set or lem in self.filler_set:
                filler_hits.append(surf)
                continue
            lemmas.append(lem)
        return lemmas, filler_hits
