# Contributing

This repository records experiments evaluating NEXCISION. Contributions should
preserve a clear separation between:

- experimental code and manifests;
- raw or generated data;
- compact source measurements and derived results;
- manuscript figures and tables.

## Before submitting a change

1. Create or activate the documented environment.
2. Install the exact NEXCISION wheel in `software/`.
3. Run `python scripts/run_experiment1_light.py` for changes affecting
   Experiment 1.
4. Run the Experiment 2 analysis entry point for changes affecting its source
   tables, derived results or figures.
5. Run `python scripts/verify_repository.py`.
6. Do not commit private datasets, generated corpora, raw benchmark logs,
   virtual environments or Python caches.
7. Document new parameters, software versions and random seeds.

Results should be reproducible from tracked scripts and manifests. Do not
manually edit a derived result without updating the code that generates it.
