.PHONY: setup experiment1-light experiment1-full

setup:
	python -m pip install -r environments/experiment1-requirements.txt
	python -m pip install software/nexcision-0.1.0-py3-none-any.whl

experiment1-light:
	python scripts/run_experiment1_light.py

experiment1-full:
	python scripts/run_experiment1_full.py
