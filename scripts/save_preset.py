from __future__ import annotations
import json, pathlib, argparse
from runlog_util import append_changelog

ap = argparse.ArgumentParser()
ap.add_argument("--threshold", type=float, required=True)
ap.add_argument("--calibrate", choices=["none","platt","isotonic"], default="platt")
ap.add_argument("--cv_mode", choices=["sgkf","loco"], default="sgkf")
ap.add_argument("--splits", type=int, default=2)
args = ap.parse_args()

pathlib.Path("config").mkdir(parents=True, exist_ok=True)
cfg = {
  "decision_threshold": args.threshold,
  "calibrate": args.calibrate,
  "cv_mode": args.cv_mode,
  "cv_splits": args.splits
}
path = pathlib.Path("config/eval_preset.json")
path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
append_changelog({
  "title":"Save eval preset",
  "notes":"固定設定を保存（再現用）",
  "metrics":{},
  "params": cfg
})
print("Wrote", path)
