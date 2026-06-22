#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
docx の校閲記録(track changes: w:ins/w:del)とコメントを著者・日付付きで抽出する。

用途:
  宗田さん(著者=" ", 2026-05)ベースと、山下先生(著者="Yuichi YAMASHITA", 2026-06-22)の
  追記差分を分離して把握し、paper1_ja.tex への反映台帳を作る。

使い方:
  python3 scripts/build/extract_docx_review.py <docx> [--author SUBSTR] [--out report.md]

出力:
  - 段落単位で、ins(挿入)/del(削除)テキストを著者・日付付きで列挙
  - コメント(本文アンカー + コメント文 + 著者 + 日付)を列挙
"""
import argparse
import sys
import zipfile
from xml.etree import ElementTree as ET

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def q(tag):
    return f"{{{W}}}{tag}"


def text_of_runs(elem):
    """elem 配下の w:t テキストを連結。"""
    parts = []
    for t in elem.iter(q("t")):
        parts.append(t.text or "")
    # 削除されたテキストは w:delText に入る
    for t in elem.iter(q("delText")):
        parts.append(t.text or "")
    return "".join(parts)


def load_comments(z):
    """comments.xml を {id: {author, date, text}} で返す。"""
    out = {}
    try:
        data = z.read("word/comments.xml")
    except KeyError:
        return out
    root = ET.fromstring(data)
    for c in root.iter(q("comment")):
        cid = c.get(q("id"))
        author = c.get(q("author")) or ""
        date = c.get(q("date")) or ""
        txt = text_of_runs(c).strip()
        out[cid] = {"author": author.strip(), "date": date, "text": txt}
    return out


def para_text_plain(p):
    """段落の確定テキスト(挿入は採用・削除は除外)。"""
    parts = []
    for node in p.iter():
        tag = node.tag
        if tag == q("t"):
            parts.append(node.text or "")
    return "".join(parts)


def extract(docx_path, author_filter=None):
    z = zipfile.ZipFile(docx_path)
    comments = load_comments(z)
    doc = ET.fromstring(z.read("word/document.xml"))

    results = []  # list of dicts per paragraph with changes/comments
    body = doc.find(q("body"))
    if body is None:
        body = doc

    for pi, p in enumerate(body.iter(q("p"))):
        ins_items = []  # (author, date, text)
        del_items = []
        comment_ids = []

        for child in p.iter():
            tag = child.tag
            if tag == q("ins"):
                a = (child.get(q("author")) or "").strip()
                d = child.get(q("date")) or ""
                t = text_of_runs(child)
                if t.strip():
                    ins_items.append((a, d, t))
            elif tag == q("del"):
                a = (child.get(q("author")) or "").strip()
                d = child.get(q("date")) or ""
                t = text_of_runs(child)
                if t.strip():
                    del_items.append((a, d, t))
            elif tag == q("commentReference"):
                comment_ids.append(child.get(q("id")))

        if not (ins_items or del_items or comment_ids):
            continue

        if author_filter:
            ins_items = [x for x in ins_items if author_filter in x[0]]
            del_items = [x for x in del_items if author_filter in x[0]]
            # コメントは著者で絞る
            comment_ids = [
                cid for cid in comment_ids
                if cid in comments and author_filter in comments[cid]["author"]
            ]
            if not (ins_items or del_items or comment_ids):
                continue

        results.append({
            "para_index": pi,
            "context": para_text_plain(p).strip()[:300],
            "ins": ins_items,
            "del": del_items,
            "comment_ids": comment_ids,
        })

    return results, comments


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("docx")
    ap.add_argument("--author", default=None, help="著者名の部分一致でフィルタ")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    results, comments = extract(args.docx, args.author)

    lines = []
    lines.append(f"# 校閲抽出: {args.docx}")
    if args.author:
        lines.append(f"\n著者フィルタ: `{args.author}`")
    n_ins = sum(len(r["ins"]) for r in results)
    n_del = sum(len(r["del"]) for r in results)
    n_com = sum(len(r["comment_ids"]) for r in results)
    lines.append(f"\n変更段落: {len(results)} / 挿入run: {n_ins} / 削除run: {n_del} / コメント: {n_com}\n")

    for r in results:
        lines.append(f"\n## 段落 #{r['para_index']}")
        if r["context"]:
            lines.append(f"> 文脈: {r['context']}")
        for a, d, t in r["del"]:
            lines.append(f"- [DEL {a} {d[:10]}] ~~{t}~~")
        for a, d, t in r["ins"]:
            lines.append(f"- [INS {a} {d[:10]}] **{t}**")
        for cid in r["comment_ids"]:
            c = comments.get(cid, {})
            lines.append(f"- [COMMENT {c.get('author','?')} {c.get('date','')[:10]}] {c.get('text','')}")

    out_text = "\n".join(lines)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(out_text)
        print(f"wrote {args.out} ({len(out_text)} chars)")
    else:
        sys.stdout.write(out_text)


if __name__ == "__main__":
    main()
