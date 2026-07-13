#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify [CHECK-A] numbers in the 66会話/74話者 paragraph against metadata."""
import pandas as pd

df = pd.read_csv("artifacts/analysis/cejc_speaker_metadata.tsv", sep="\t")
print("records (rows):", len(df))
print("unique conversations:", df["conversation_id"].nunique())
print("unique speakers (cejc_person_id):", df["cejc_person_id"].nunique())

# conversations per speaker
per_spk = df.groupby("cejc_person_id")["conversation_id"].nunique()
dup = per_spk[per_spk >= 2]
single = per_spk[per_spk == 1]
print("speakers in >=2 conversations:", len(dup))
print("speakers in exactly 1 conversation:", len(single))

# records belonging to duplicate speakers
recs_dup = df[df["cejc_person_id"].isin(dup.index)]
print("records from duplicate speakers:", len(recs_dup),
      f"({len(recs_dup)/len(df)*100:.1f}%)")

# gender by unique speaker
g_spk = df.drop_duplicates("cejc_person_id")["gender"].value_counts()
print("speaker-level gender:", dict(g_spk))
# gender by record
g_rec = df["gender"].value_counts()
print("record-level gender:", dict(g_rec))
