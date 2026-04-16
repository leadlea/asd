# Use bash for pipes/tee
SHELL := /bin/bash

.PHONY: loco ablate baseline clean eval_best ablate_best infer_best \
        reproduce_bn2015 reproduce_bn2015_log show_repro clean_repro \
        baseline-prep baseline-dirs baseline-compare baseline-all \
        docx clean-docx \
        dose-manipulate dose-verify dose-dirs dose-report dose-response

# ==== Existing variables ====
PYTHON := .venv/bin/python
FEAT = data/processed/features_merged.csv

# ==== Reproduction config (Bang & Nadig 2015) ====
CONFIG       := dual_bn2015.yaml
REPRO_HTML   := docs/Compare.html
REPRO_DIR    := reports/reproduction/bang_nadig_2015
REPRO_LOG    := logs/reproduce_bn2015.log

# ==== Existing targets ====
loco:
	python scripts/loco_eval.py --feat_csv $(FEAT) --out_json reports/loco_report.json --out_png reports/figures/loco_auc.png

ablate:
	python scripts/ablation_eval.py --feat_csv $(FEAT) --out_json reports/ablation_report.json --out_png reports/figures/ablation_delta.png

baseline:
	@echo "Run your existing baseline pipeline"

clean:
	rm -f reports/*_report.json
	rm -f reports/figures/*.png

eval_best:
	python scripts/loco_eval.py --feat_csv data/processed/features_merged.csv \
	  --mode sgkf --splits 2 --threshold 0.55 --calibrate platt

ablate_best:
	python scripts/ablation_eval.py --feat_csv data/processed/features_merged.csv \
	  --threshold 0.55

infer_best:
	python scripts/inference_cli.py --feat_csv data/processed/features_merged.csv \
	  --out_csv reports/pred_top5.csv

# ==== New: Reproduction (Bang & Nadig 2015) ====

# 1) ワンコマンド再現（ログは標準出力）
reproduce_bn2015:
	python bn2015_dual_run.py --config $(CONFIG)

# 2) ログ保存付きの再現（推奨）
reproduce_bn2015_log:
	mkdir -p logs
	python bn2015_dual_run.py --config $(CONFIG) 2>&1 | tee $(REPRO_LOG)

# 3) 生成物の存在確認（ざっくり）
show_repro:
	@echo "== Reproduction outputs =="
	@ls -lh $(REPRO_HTML) || true
	@ls -lh $(REPRO_DIR)/*.csv || true
	@echo "== Log =="
	@ls -lh $(REPRO_LOG) || true

# 4) 再現物クリーン
clean_repro:
	rm -rf $(REPRO_DIR) $(REPRO_HTML) $(REPRO_LOG)
# ==== Pragmatics add-on (non-invasive) ====
PRAG_MOD  := src/features/pragmatics_basic.py
PRAG_IN   := data/interim/utterances.csv
PRAG_OUT  := data/processed/pragmatics_basic.csv
DASH_HTML := docs/bn2015_dashboard.html

pragmatics_basic:
	python $(PRAG_MOD) --in_csv $(PRAG_IN) --out_csv $(PRAG_OUT)

dashboard_plus:  ## requires reproduce_bn2015 to have produced dyads/desc/ttest
	python make_dashboard.py \
		--dyads $(REPRO_DIR)/dyads.csv \
		--desc $(REPRO_DIR)/table3_descriptives_en.csv \
		--ttest $(REPRO_DIR)/table2_en_ttests.csv \
		--out $(DASH_HTML) \
		--prag $(PRAG_OUT)
	@echo "Wrote $(DASH_HTML) (add-on section included if $(PRAG_OUT) exists)"

# ==== Baseline Validation (LLM content dependency check) ====
# 条件2・条件3のmonologues生成（LLM採点・ensemble実行は手動）

UTT_PQ   := artifacts/_tmp_utt/cejc_utterances/part-00000.parquet
MONO_PQ  := artifacts/cejc/monologues_cejc_home2_hq1_v1.parquet
BL_DIR   := artifacts/baseline
COND1_TSV := artifacts/analysis/results/ensemble_perm_v4/ensemble_summary.tsv
COND2_TSV := artifacts/analysis/results/baseline_validation/condition_summary/ensemble_summary.tsv
COND3_TSV := artifacts/analysis/results/baseline_validation/condition_random/ensemble_summary.tsv
COMP_TSV  := artifacts/analysis/results/baseline_validation/comparison_summary.tsv

baseline-prep:
	python scripts/baseline/gen_summary_monologues.py \
	  --utterances_parquet $(UTT_PQ) \
	  --monologues_parquet $(MONO_PQ) \
	  --out_parquet $(BL_DIR)/monologues_summary.parquet
	python scripts/baseline/gen_random_monologues.py \
	  --monologues_parquet $(MONO_PQ) \
	  --out_parquet $(BL_DIR)/monologues_random.parquet \
	  --mapping_csv $(BL_DIR)/shuffle_mapping.csv \
	  --seed 42

baseline-dirs:
	python scripts/baseline/prepare_ensemble_dirs.py \
	  --scores_dir artifacts/big5/llm_scores \
	  --out_summary_dir artifacts/big5/llm_scores_summary \
	  --out_random_dir artifacts/big5/llm_scores_random

baseline-compare:
	python scripts/baseline/compare_conditions.py \
	  --cond1_tsv $(COND1_TSV) \
	  --cond2_tsv $(COND2_TSV) \
	  --cond3_tsv $(COND3_TSV) \
	  --out_tsv $(COMP_TSV) \
	  --threshold 0.1

baseline-all: baseline-prep baseline-dirs baseline-compare
	@echo "✓ baseline-all 完了（LLM採点・ensemble実行は手動）"


# ==== Google Docs Export (pandoc LaTeX → docx) ====
PAPER_TEX  := paper1_ja.tex
PAPER_DOCX := reports/paper1_ja.docx
FIG_DIR    := reports/paper_figs_v2
REF_DOCX   := templates/reference.docx

# --reference-doc is applied only when templates/reference.docx exists
PANDOC_REF := $(if $(wildcard $(REF_DOCX)),--reference-doc=$(REF_DOCX),)

docx: $(PAPER_DOCX)

$(PAPER_DOCX): $(PAPER_TEX)
	@mkdir -p $(dir $(PAPER_DOCX))
	pandoc $(PAPER_TEX) \
	  -f latex -t docx \
	  --resource-path=.:$(FIG_DIR) \
	  $(PANDOC_REF) \
	  -o $(PAPER_DOCX)
	@echo ""
	@echo "✓ Generated $(PAPER_DOCX)"
	@echo ""
	@echo "  Known limitations (要手動確認):"
	@echo "  - bxjsarticle固有の書式はdocxに反映されない"
	@echo "  - LaTeX数式 (amsmath) の一部が崩れる可能性あり"
	@echo "  - \\graphicspath による図の埋め込みは手動確認が必要"
	@echo "  - booktabs/longtable の罫線スタイルが簡略化される"
	@echo "  - hyperref のリンクが失われる場合がある"
	@echo "  - dvipdfmx 固有のオプションは無視される"
	@echo ""
	@echo "  File: $(PAPER_DOCX)"
	@echo "  → Google Drive にアップロードして共同編集可能"

clean-docx:
	rm -f $(PAPER_DOCX)


# ==== Feature Dose-Response 実験 ====
# 3特徴量（FILL, YESNO, OIR）× 3 Dose Level（×0, ×1, ×3）
# ×1 は既存結果を再利用。LLM採点・ensemble実行は手動。
# DRYRUN=1 make dose-response で dry-run モード

DOSE_MONO_PQ  := artifacts/cejc/monologues_cejc_home2_hq1_v1.parquet
DOSE_OUT      := artifacts/dose_response
DOSE_SCORES   := artifacts/big5/llm_scores
DOSE_RESULTS  := artifacts/analysis/results/dose_response
DOSE_BASELINE := artifacts/analysis/results/ensemble_perm_v4/ensemble_summary.tsv
DOSE_SEED     := 42

# dry-run flag: DRYRUN=1 make dose-manipulate
ifdef DRYRUN
  DOSE_DRYRUN := --dry-run
else
  DOSE_DRYRUN :=
endif

dose-manipulate:
	@echo "=== Dose-Response: テキスト操作（FILL, YESNO, OIR）==="
	PYTHONPATH=. $(PYTHON) scripts/dose_response/gen_dose_monologues.py \
	  --monologues_parquet $(DOSE_MONO_PQ) \
	  --target_feature FILL \
	  --dose_levels 0,1,3 \
	  --out_dir $(DOSE_OUT) \
	  --seed $(DOSE_SEED) \
	  $(DOSE_DRYRUN)
	PYTHONPATH=. $(PYTHON) scripts/dose_response/gen_dose_monologues.py \
	  --monologues_parquet $(DOSE_MONO_PQ) \
	  --target_feature YESNO \
	  --dose_levels 0,1,3 \
	  --out_dir $(DOSE_OUT) \
	  --seed $(DOSE_SEED) \
	  $(DOSE_DRYRUN)
	PYTHONPATH=. $(PYTHON) scripts/dose_response/gen_dose_monologues.py \
	  --monologues_parquet $(DOSE_MONO_PQ) \
	  --target_feature OIR \
	  --dose_levels 0,1,3 \
	  --out_dir $(DOSE_OUT) \
	  --seed $(DOSE_SEED) \
	  $(DOSE_DRYRUN)
	@echo "✓ dose-manipulate 完了"

dose-verify:
	@echo "=== Dose-Response: 特徴量検証 ==="
	PYTHONPATH=. $(PYTHON) scripts/dose_response/verify_features.py \
	  --original_parquet $(DOSE_MONO_PQ) \
	  --dose_dir $(DOSE_OUT) \
	  --target_feature FILL
	PYTHONPATH=. $(PYTHON) scripts/dose_response/verify_features.py \
	  --original_parquet $(DOSE_MONO_PQ) \
	  --dose_dir $(DOSE_OUT) \
	  --target_feature YESNO
	PYTHONPATH=. $(PYTHON) scripts/dose_response/verify_features.py \
	  --original_parquet $(DOSE_MONO_PQ) \
	  --dose_dir $(DOSE_OUT) \
	  --target_feature OIR
	@echo "✓ dose-verify 完了"

dose-dirs:
	@echo "=== Dose-Response: ensemble互換ディレクトリ構築 ==="
	PYTHONPATH=. $(PYTHON) scripts/dose_response/prepare_ensemble_dirs.py \
	  --scores_dir $(DOSE_SCORES) \
	  --dose_levels 0,3 \
	  --target_feature FILL \
	  --out_dir artifacts/big5
	PYTHONPATH=. $(PYTHON) scripts/dose_response/prepare_ensemble_dirs.py \
	  --scores_dir $(DOSE_SCORES) \
	  --dose_levels 0,3 \
	  --target_feature YESNO \
	  --out_dir artifacts/big5
	PYTHONPATH=. $(PYTHON) scripts/dose_response/prepare_ensemble_dirs.py \
	  --scores_dir $(DOSE_SCORES) \
	  --dose_levels 0,3 \
	  --target_feature OIR \
	  --out_dir artifacts/big5
	@echo "✓ dose-dirs 完了"

dose-report:
	@echo "=== Dose-Response: 分析レポート生成 ==="
	PYTHONPATH=. $(PYTHON) scripts/dose_response/dose_response_report.py \
	  --results_dir $(DOSE_RESULTS) \
	  --baseline_tsv $(DOSE_BASELINE) \
	  --target_feature FILL \
	  --control_feature OIR \
	  --verification_tsv $(DOSE_OUT)/feature_verification_FILL.tsv \
	  --out_dir $(DOSE_OUT)
	PYTHONPATH=. $(PYTHON) scripts/dose_response/dose_response_report.py \
	  --results_dir $(DOSE_RESULTS) \
	  --baseline_tsv $(DOSE_BASELINE) \
	  --target_feature YESNO \
	  --control_feature OIR \
	  --verification_tsv $(DOSE_OUT)/feature_verification_YESNO.tsv \
	  --out_dir $(DOSE_OUT)
	@echo "✓ dose-report 完了"

dose-response: dose-manipulate dose-verify
	@echo ""
	@echo "============================================================"
	@echo "  dose-response パイプライン完了（自動実行分）"
	@echo "============================================================"
	@echo ""
	@echo "  次の手動ステップ:"
	@echo "    1. bash scripts/dose_response/run_scoring_dose.sh   # LLM採点（AWS Bedrock）"
	@echo "    2. make dose-dirs                                    # ensemble互換ディレクトリ構築"
	@echo "    3. bash scripts/dose_response/run_ensemble_dose.sh  # ensemble permutation test"
	@echo "    4. make dose-report                                  # 分析レポート生成"
	@echo ""
