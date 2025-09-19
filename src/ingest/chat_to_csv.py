#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse, os, csv, re
from pathlib import Path

SPEAKER_LINE = re.compile(r"^\*([A-Z]{3}):\s*(.*)$")

def parse_cha(path: Path):
    """超簡易CHATパーサ：行頭 *XXX: の発話だけ拾う。時間タグは未対応。"""
    file_id = path.stem
    rows = []
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = SPEAKER_LINE.match(line.strip())
            if not m: 
                continue
            speaker = m.group(1)
            utt = m.group(2).strip()
            # CHATの語末記号や余計なスペースの軽い正規化
            utt = re.sub(r"\s+", " ", utt)
            rows.append({
                "file_id": file_id,
                "speaker": speaker,
                "utt": utt,
                "start_ms": "",
                "end_ms": ""
            })
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in_dir", required=True)
    ap.add_argument("--out_csv", required=True)
    args = ap.parse_args()

    in_dir = Path(args.in_dir)
    files = list(in_dir.rglob("*.cha")) + list(in_dir.rglob("*.cha.gz")) + list(in_dir.rglob("*.cha.xml"))
    total = 0
    os.makedirs(Path(args.out_csv).parent, exist_ok=True)
    with open(args.out_csv, "w", newline="", encoding="utf-8") as o:
        w = csv.DictWriter(o, fieldnames=["file_id","speaker","utt","start_ms","end_ms"])
        w.writeheader()
        for p in files:
            # .gz/.xmlは今回は素通り（.cha推奨）。必要なら展開/整形を追加。
            if p.suffix != ".cha":
                continue
            rows = parse_cha(p)
            for r in rows:
                w.writerow(r)
            total += len(rows)
    print(f"wrote {total} utterances -> {args.out_csv}")

if __name__ == "__main__":
    main()
