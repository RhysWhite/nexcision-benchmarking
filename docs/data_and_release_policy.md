# Data and release policy

## Git history

Track:

- source code and benchmark manifests;
- small fixed test fixtures;
- compact measured-result tables;
- system and software metadata;
- derived summaries and figure-generation scripts;
- final manuscript figures and tables.

Do not track:

- regenerated large matrices;
- filtered multi-gigabyte outputs;
- temporary working directories;
- repeated Slurm logs unless specifically required for a frozen release;
- private or governance-restricted genomic data;
- virtual environments and Python caches.

## Tagged releases

A manuscript or benchmark release should contain:

- the exact NEXCISION wheel and checksum;
- the benchmarking repository commit;
- frozen manifests and environment files;
- compact measured results and system metadata;
- summary results and publication figures;
- optional compressed logs or raw artefacts as release assets.

Large frozen datasets should be archived as release assets or in an external
research-data repository rather than committed repeatedly to Git history.
