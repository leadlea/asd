# Bang & Nadig (2015, Autism Research) — English subset Reproduction Kit

**Target table**: Table 2 (English) — mother MLU (words/utterance)  
Paper values: ASD 5.06 (SD 0.92); TYP 5.40 (SD 0.81)

## Steps
1) Download the *English* transcripts for the Nadig dataset (ASDBank/CHILDES). Put them under one folder.
2) Edit `reproduce_bang_nadig_2015.yaml`: set `dataset.transcripts_dir` to your folder path.
3) Run:
```bash
python parse_cha_compute_mlu.py --config reproduce_bang_nadig_2015.yaml
```
4) Check outputs:
- `per_mother_mlu.csv`
- `group_summary.csv`
- `bn2015_reproduction_report.md` (compares our means to paper means with tolerances)

### Tips
- If group labels (ASD/TYP) aren't inferable from `@ID` lines, create a CSV `file,group` and set `group_infer.method: csv` (you can extend the script to read it).
- Small deltas (±0.1–0.15) are acceptable due to tokenization differences.

### Data policy
- Do not redistribute `.cha`. Share aggregate numbers only. Respect TalkBank terms.
