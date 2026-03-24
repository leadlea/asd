#!/usr/bin/env python3
"""紙芝居スライド生成スクリプト

Results構成に対応した6枚のスライドを1枚1図で構成するHTML生成スクリプト。
各スライドに (a) タイトル、(b) 図表（imgタグ）、(c) 結論テキスト（1〜2文）を含む。
画像不在時はプレースホルダーテキスト「[図表未生成: {filename}]」を表示する。

出力: reports/paper_figs_v2/kamishibai_slides.html
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Slide:
    """1枚のスライドを表すデータ構造"""

    number: int
    title: str
    images: list[str]  # 画像ファイル名のリスト（1枚 or 複数枚）
    conclusion: str


# --- スライド定義 -----------------------------------------------------------

SLIDES: list[Slide] = [
    Slide(
        number=1,
        title="提案特徴量の分布",
        images=["fig_feature_distribution.png"],
        conclusion=(
            "18特徴量は適度なばらつきを持ち、"
            "個人差を捉える指標として有用である。"
        ),
    ),
    Slide(
        number=2,
        title="カテゴリ内/間相関",
        images=["fig_corr_heatmap_block.png"],
        conclusion=(
            "同一カテゴリ内で高相関を示す一方、"
            "カテゴリ間は独立性が高い。"
        ),
    ),
    Slide(
        number=3,
        title="コーパス基本情報との関連",
        images=["fig_metadata_gender.png", "fig_metadata_age.png"],
        conclusion=(
            "性別・年齢と一部特徴量に有意な関連が認められた。"
        ),
    ),
    Slide(
        number=4,
        title="Big5との関連 — Permutation Test",
        images=["fig_permutation_C_bar.png"],
        conclusion=(
            "Conscientiousness（C）は4教師中3教師で有意であり、"
            "教師非依存の頑健性を示す。"
        ),
    ),
    Slide(
        number=5,
        title="Teacher間一致度",
        images=["fig_teacher_heatmap.png"],
        conclusion=(
            "C: mean r=0.699で最高であり、"
            "仮想教師として最も安定している。"
        ),
    ),
    Slide(
        number=6,
        title="Bootstrap Top Drivers",
        images=["fig_bootstrap_C_radar.png"],
        conclusion=(
            "FILL_has_any, IX_oirmarker_after_question_rate, "
            "PG_speech_ratioが上位ドライバーである。"
        ),
    ),
]


# --- HTML / CSS テンプレート -------------------------------------------------

CSS = """\
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: "Hiragino Kaku Gothic ProN", "Noto Sans JP", "Meiryo", sans-serif;
  background: #f5f5f5;
  color: #333;
}
.slide {
  width: 960px;
  min-height: 720px;
  margin: 40px auto;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.10);
  padding: 48px 56px 40px;
  display: flex;
  flex-direction: column;
  align-items: center;
  page-break-after: always;
}
.slide-number {
  align-self: flex-end;
  font-size: 14px;
  color: #999;
  margin-bottom: 8px;
}
.slide-title {
  font-size: 32px;
  font-weight: 700;
  text-align: center;
  margin-bottom: 24px;
  color: #1a1a2e;
}
.slide-images {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 24px;
  width: 100%;
  margin-bottom: 24px;
}
.slide-images img {
  max-width: 100%;
  max-height: 440px;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
}
.slide-images.multi img {
  max-width: 48%;
  max-height: 380px;
}
.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 400px;
  height: 300px;
  background: #fafafa;
  border: 2px dashed #ccc;
  border-radius: 8px;
  color: #999;
  font-size: 16px;
  text-align: center;
  padding: 16px;
}
.slide-conclusion {
  font-size: 20px;
  line-height: 1.6;
  text-align: center;
  color: #444;
  padding: 16px 24px;
  background: #f0f4ff;
  border-radius: 6px;
  width: 100%;
}
.nav {
  text-align: center;
  font-size: 14px;
  color: #888;
  margin: 8px 0 32px;
}
"""


def _image_html(filename: str, out_dir: Path) -> str:
    """画像が存在すればimgタグ、なければプレースホルダーを返す"""
    if (out_dir / filename).exists():
        return f'<img src="{filename}" alt="{filename}">'
    return f'<div class="placeholder">[図表未生成: {filename}]</div>'


def generate_slides_html(out_dir: Path) -> str:
    """6枚のスライドを含む自己完結型HTMLを生成する"""
    total = len(SLIDES)
    slide_blocks: list[str] = []

    for slide in SLIDES:
        # 画像セクション
        multi_class = " multi" if len(slide.images) > 1 else ""
        images_html = "\n        ".join(
            _image_html(img, out_dir) for img in slide.images
        )

        # ナビゲーション
        nav_parts: list[str] = []
        if slide.number > 1:
            nav_parts.append("← prev")
        nav_parts.append(f"{slide.number} / {total}")
        if slide.number < total:
            nav_parts.append("next →")
        nav_html = " &nbsp;|&nbsp; ".join(nav_parts)

        block = f"""\
    <div class="slide" id="slide-{slide.number}">
      <div class="slide-number">Slide {slide.number} / {total}</div>
      <div class="slide-title">{slide.title}</div>
      <div class="slide-images{multi_class}">
        {images_html}
      </div>
      <div class="slide-conclusion">{slide.conclusion}</div>
    </div>
    <div class="nav">{nav_html}</div>"""
        slide_blocks.append(block)

    slides_body = "\n\n".join(slide_blocks)

    html = f"""\
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>紙芝居スライド — 相互行為特徴量の定量化指標の提案</title>
  <style>
{CSS}  </style>
</head>
<body>

{slides_body}

</body>
</html>
"""
    return html


def main() -> None:
    parser = argparse.ArgumentParser(
        description="紙芝居スライド（1枚1図）のHTML生成"
    )
    parser.add_argument(
        "--out_dir",
        type=str,
        default="reports/paper_figs_v2/",
        help="出力ディレクトリ（画像もここから参照）",
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    html = generate_slides_html(out_dir)
    out_path = out_dir / "kamishibai_slides.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"✅ 紙芝居スライドを生成しました: {out_path}")


if __name__ == "__main__":
    main()
