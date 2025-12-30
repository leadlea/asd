from __future__ import annotations
import json, pathlib
from runlog_util import append_changelog
thr_json = pathlib.Path("reports/threshold_report.json")
if not thr_json.exists():
    raise SystemExit("reports/threshold_report.json が見つかりません。先に threshold_search.py を実行してください。")
best = json.loads(thr_json.read_text(encoding="utf-8"))["best"]
pathlib.Path("config").mkdir(exist_ok=True, parents=True)
pathlib.Path("config/model_config.json").write_text(
    json.dumps({"decision_threshold": best["threshold"]}, ensure_ascii=False, indent=2),
    encoding="utf-8"
)
append_changelog({
    "title": "Freeze decision threshold",
    "notes": "最適しきい値をモデル設定に固定",
    "metrics": {"threshold": best["threshold"], "F1*": best["f1"], "BA*": best["ba"]},
    "params": {"config": "config/model_config.json"}
})
print("Wrote config/model_config.json with decision_threshold =", best["threshold"])
