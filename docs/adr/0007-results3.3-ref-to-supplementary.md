# ADR-0007: Results 3.3 のメタ紐付け参照を付録へ付け替え

- 状態: Accepted
- 日付: 2026-06-22
- 決定者: 福原玄（NCNP共同研究・筆頭）
- 関連: `paper1_ja.tex`（Results 3.3, 付録）, ADR-0004/0006

## コンテキスト

ADR-0004でCEJCメタ情報の紐付け詳細を付録（`sec:supp_dataset`）へ移送したが、Results 3.3の紐付け記述は旧参照「（2.1節参照）」のままだった。2.1は外形のみのため、実体の参照先と不整合。

## 決定

1. Results 3.3 の `conversation_id × cejc_person_id をキーに紐付けた（2.1節参照）` の参照を `付録\ref{sec:supp_dataset}` に付け替え。
2. Discussion の `GroupKFold（cejc_person_id単位）` は文脈内で必要なため**そのまま残す**（福原判断）。

## 検証

- uplatex 2パス＋dvipdfmx: 正常、47ページ、未解決の参照・引用なし（`sec:supp_dataset` 解決）。

## 次の1手

申し送り項目を解消。次の個別修正対象セクションの指示を待つ。
