# 日本語コーパス 9分窓パイプライン（MiiPro対応 / lemma×短単位語）

英語README_JAの構成と互換の発想で、MiiPro等の日本語 .cha を **fugashi(MeCab)+UniDic** を主系、**SudachiPy(dict_full, mode=C)** を補系に用いて、
**CHI（子）と親（MOT等）**を同一9分窓で集計します。語彙多様性（NDW=types）、トークン数、MLU（短単位語/発話）を出力し、
簡易メタ解析（例: MOT MLU−CHI MLU の Hedges g）まで HTML ダッシュボードにまとめます。

## 依存関係
```bash
python -m pip install -U fugashi unidic-lite sudachipy sudachidict-full pandas numpy pyyaml
# 可能なら UniDic 本体も: python -m unidic download
```

## 使い方
```
repo_root/
  MiiPro/               # ← 既にあるローカル生データ
  jp_pipeline/
    compute_metrics.py
    cha_utils.py
    jp_tokenizer.py
    build_windows.py
    config_jp.yaml
    fillers_ja.txt
  run_jp_pipeline.sh
```

1. `config_jp.yaml` の `corpus_dir` をローカルの MiiPro ルートに合わせる
2. 実行: `./run_jp_pipeline.sh ./jp_pipeline/config_jp.yaml`
3. 出力: `out/jp/jp_sessions.csv`, `out/jp/jp_descriptives.csv`, `out/jp/jp_meta.csv`, `docs/jp_miipro_dashboard.html`

## 実装メモ
- **フィラー除外**: `fillers_ja.txt` に列挙（えー、あの、うん、うーん、…）。語彙（types/NDW, MLU の分子）から除外し、`out/jp/filler_hits.csv` に記録。
- **9分窓**: CHA の `start_end` タイムスタンプがあれば [t0, t0+9min] を採用。無い場合は `assume_session_minutes=70` を基に **発話数×(9/70)** を近似。
- **lemma**: 主系 fugashi×UniDic の lemma、OOV/表記ゆらぎは SudachiPy(dict_full, mode=C) の `normalized_form()` で補強。
- **MLU**: 短単位語（lemma）/発話の平均。

## メタ解析について
- グループ分け（ASD/TYP）が無い前提のため、例として **親（MOT等）と子（CHI）の MLU 差**をセッション横断で Hedges g 化し、固定効果近似で 95%CI を表示。
- 比較軸を変えたい場合（例: CHI NDW の年齢推移など）は、将来 `jp_meta.py` を追加して、任意のコントラストを指定できるようにする想定です。
