# Use bash for pipes/tee
SHELL := /bin/bash

.PHONY: loco ablate baseline clean eval_best ablate_best infer_best \
        reproduce_bn2015 reproduce_bn2015_log show_repro clean_repro

# ==== Existing variables ====
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
