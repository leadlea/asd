# Reproduction — Bang & Nadig (2015) — English subset (Child speech: CHI MLU)

**Metric**: CHI MLU (words/utterance)

**Aggregation**: per child -> group

**Token source**: %mor

## Results (ours vs paper)

- ASD: ours mean=3.283, sd=0.872; paper mean=None, sd=None → —
- TYP: ours mean=3.227, sd=0.89; paper mean=None, sd=None → —

## Notes
- Gem: setting=OFF, windows present=0/38; timestamps-missing -> included.
- Language: sessions that include English are kept (strict_english_only may be off).
- Tokens: punctuation stripped; alphabetic+contractions; fillers/codes dropped. If use_mor_tokens=true, %mor-based counting with surface fallback.
- Aggregation: child-level means when enabled; population SD for descriptives.