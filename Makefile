.PHONY: setup experiment1-light experiment1-full experiment2-analysis audit

setup:
	python -m pip install -r environments/experiment1-requirements.txt
	python -m pip install software/nexcision-0.1.0-py3-none-any.whl

experiment1-light:
	python scripts/run_experiment1_light.py

experiment1-full:
	python scripts/run_experiment1_full.py

experiment2-analysis:
	python experiments/experiment_2_scalability/analysis/analyse_formal_results.py --job-id 2432330

audit:
	python scripts/verify_repository.py
