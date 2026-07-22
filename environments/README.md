# Software environments

Each experiment has an explicit dependency file. NEXCISION itself is installed
from the exact wheel stored in `software/`.

## Experiment 1

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r environments/experiment1-requirements.txt
python -m pip install software/nexcision-0.1.0-py3-none-any.whl
```

## Experiment 2 analysis

The formal benchmark runner itself uses only the Python standard library and
the frozen NEXCISION wheel. Reproducing the derived tables and figures requires:

```bash
python -m venv .venv-analysis
source .venv-analysis/bin/activate
python -m pip install --upgrade pip
python -m pip install -r environments/experiment2-analysis-requirements.txt
python experiments/experiment_2_scalability/analysis/analyse_formal_results.py \
  --job-id 2432330
```

The pinned versions match those used to generate the committed Experiment 2
figures.

Record an environment when creating a new frozen release with:

```bash
python --version
python -m pip freeze
```
