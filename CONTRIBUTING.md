# Contributing

This repository records experiments evaluating NEXCISION. Contributions should preserve a clear separation between:

- experimental code and manifests;
- raw or generated data;
- derived results;
- manuscript figures and tables.

## Before submitting a change

1. Create or activate the documented environment.
2. Install the exact NEXCISION wheel in `software/`.
3. Run `python scripts/run_experiment1_light.py` for changes affecting Experiment 1.
4. Do not commit private datasets, generated corpora, raw benchmark logs or virtual environments.
5. Document new parameters, software versions and random seeds.

Results should be reproducible from tracked scripts and manifests. Do not manually edit a derived result without updating the code that generates it.
