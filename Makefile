.PHONY: loco ablate baseline clean
FEAT=data/processed/features_merged.csv

loco:
	python scripts/loco_eval.py --feat_csv $(FEAT) --out_json reports/loco_report.json --out_png reports/figures/loco_auc.png

ablate:
	python scripts/ablation_eval.py --feat_csv $(FEAT) --out_json reports/ablation_report.json --out_png reports/figures/ablation_delta.png

baseline:
	@echo "Run your existing baseline pipeline"

clean:
	rm -f reports/*_report.json
	rm -f reports/figures/*.png

.PHONY: eval_best ablate_best
eval_best:
	python scripts/loco_eval.py --feat_csv data/processed/features_merged.csv \
	  --mode sgkf --splits 2 --threshold 0.55 --calibrate platt

ablate_best:
	python scripts/ablation_eval.py --feat_csv data/processed/features_merged.csv \
	  --threshold 0.55

.PHONY: infer_best
infer_best:
	python scripts/inference_cli.py --feat_csv data/processed/features_merged.csv \
	  --out_csv reports/pred_top5.csv
