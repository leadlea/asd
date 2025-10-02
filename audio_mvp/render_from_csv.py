
import os, sys, argparse, pandas as pd
from types import SimpleNamespace as Row

# audio_mvp を import パスに追加
sys.path.insert(0, os.path.dirname(__file__))
from html_report import render_html

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="segments/turns/prosody/pragmatics.csv があるディレクトリ")
    ap.add_argument("--title", required=True)
    args = ap.parse_args()

    d = Path(args.dir)
    seg_df  = pd.read_csv(d/"segments.csv")
    turns_df= pd.read_csv(d/"turns.csv")
    pros_df = pd.read_csv(d/"prosody.csv")
    prag_df = pd.read_csv(d/"pragmatics.csv")

    segments = [Row(start=float(r.start), end=float(r.end), speaker=str(r.speaker), text=str(r.text))
                for r in seg_df.itertuples(index=False)]
    turns    = [Row(**r._asdict()) for r in turns_df.itertuples(index=False)]
    prosody  = [Row(**r._asdict()) for r in pros_df.itertuples(index=False)]
    prag     = [Row(**r._asdict()) for r in prag_df.itertuples(index=False)]

    html = render_html(args.title, segments, turns, prosody, prag)
    (d/"report.html").write_text(html)
    print("wrote:", d/"report.html")

if __name__ == "__main__":
    from pathlib import Path
    main()
