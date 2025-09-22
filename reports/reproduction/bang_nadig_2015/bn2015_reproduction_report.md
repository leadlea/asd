# Reproduction — Bang & Nadig (2015) Autism Research — English subset (Mother input)

**Metric**: Mother MLU (words/utterance)

**Aggregation**: per mother -> group

**Token source**: %mor

## Results (ours vs paper)

- ASD: ours mean=4.896, sd=0.651; paper mean=5.06, sd=0.92 → OK
- TYP: ours mean=5.385, sd=0.806; paper mean=5.4, sd=0.81 → OK

## Notes
- Gem: setting=OFF, windows present=0/38; timestamps-missing -> included.
- Language: sessions that include English are kept (strict_english_only may be off).
- Tokens: punctuation stripped; alphabetic+contractions; fillers/codes dropped. If use_mor_tokens=true, %mor-based counting with surface fallback.
- Aggregation: mother-level means when enabled; population SD for descriptives.