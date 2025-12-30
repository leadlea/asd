from __future__ import annotations
import json, datetime, pathlib

def append_changelog(entry: dict, changelog_path: str = "CHANGELOG.md") -> None:
    p = pathlib.Path(changelog_path)
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = f"### {ts} — {entry.get('title','Run')}\n"
    lines = [header]
    if 'notes' in entry and entry['notes']:
        lines.append(f"- {entry['notes']}\n")
    if 'metrics' in entry:
        m = entry['metrics']
        kv = ", ".join(f"{k}={v:.3f}" if isinstance(v,(int,float)) else f"{k}={v}" for k,v in m.items())
        lines.append(f"- metrics: {kv}\n")
    if 'params' in entry and entry['params']:
        js = json.dumps(entry['params'], ensure_ascii=False)
        lines.append(f"- params: `{js}`\n")
    lines.append("\n")
    if p.exists():
        p.write_text(p.read_text(encoding="utf-8") + "".join(lines), encoding="utf-8")
    else:
        p.write_text("# CHANGELOG\n\n" + "".join(lines), encoding="utf-8")

def write_run_json(obj: dict, out_json: str) -> None:
    p = pathlib.Path(out_json)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
