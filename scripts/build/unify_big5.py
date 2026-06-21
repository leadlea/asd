# -*- coding: utf-8 -*-
"""全ドキュメント・コードで「Big Five」->「Big5」に統一する一回限りスクリプト。"""
import os

EXTS = (".tex", ".md", ".html", ".py", ".json")
SKIP = {".git", "build", "node_modules", "__pycache__"}
changed = []
for dp, dns, fns in os.walk("."):
    dns[:] = [d for d in dns if d not in SKIP]
    for fn in fns:
        if not fn.endswith(EXTS):
            continue
        p = os.path.join(dp, fn)
        try:
            t = open(p, encoding="utf-8").read()
        except (UnicodeDecodeError, IsADirectoryError):
            continue
        if "Big Five" not in t:
            continue
        n = t.count("Big Five")
        open(p, "w", encoding="utf-8").write(t.replace("Big Five", "Big5"))
        changed.append((p, n))
for p, n in sorted(changed):
    print(f"{n:4d}  {p}")
print(f"--- files: {len(changed)}, replacements: {sum(n for _,n in changed)}")
