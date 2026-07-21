# Software environments

Each experiment has an explicit dependency file. NEXCISION itself is installed from the exact wheel stored in `software/`.

## Experiment 1

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r environments/experiment1-requirements.txt
python -m pip install software/nexcision-0.1.0-py3-none-any.whl
```

Record the final environment with:

```bash
python --version
python -m pip freeze
```
