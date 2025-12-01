from fugashi import Tagger
tagger = Tagger()
DM_TOKENS = set(["ね","よ","まあ","でも","その","えっと","あの","さ"])
MENTAL_LEMMAS = set(["思う","考える","知る","分かる","感じる","欲しい","好きだ","嫌いだ","信じる","覚える","忘れる","気づく","願う"])
FILLERS = set(["え","えー","えっと","あの","うーん","ま","その"])
def tokenize(text):
    tokens = []
    for m in tagger(text):
        surf = m.surface
        lem = m.feature.lemma if hasattr(m.feature, "lemma") and m.feature.lemma else surf
        pos = m.feature.pos1 if hasattr(m.feature, "pos1") else ""
        tokens.append({"surface":surf, "lemma":lem, "pos":pos})
    return tokens
def count_metrics(utterances):
    n_utts = len(utterances); all_tokens = []; n_questions = 0; dm_count = 0; mental_count = 0
    for utt in utterances:
        text = utt.strip()
        if not text: continue
        if text.endswith("？") or text.endswith("?"): n_questions += 1
        toks = [t for t in tokenize(text) if t["surface"] not in FILLERS]
        all_tokens.extend(toks)
        dm_count += sum(1 for t in toks if t["surface"] in DM_TOKENS)
        mental_count += sum(1 for t in toks if t["lemma"] in MENTAL_LEMMAS)
    n_tokens = len(all_tokens)
    n_types  = len(set(t["lemma"] for t in all_tokens)) if n_tokens else 0
    mlu      = (n_tokens / max(1, n_utts)) if n_utts else 0.0
    per100   = lambda x: 100.0 * x / max(1, n_tokens)
    return {"n_utts":n_utts,"n_tokens":n_tokens,"n_types":n_types,"mlu":mlu,
            "question_rate":(n_questions / max(1, n_utts)),
            "dm_per_100t":per100(dm_count),"mental_per_100t":per100(mental_count)}
