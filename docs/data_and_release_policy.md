# Data and release policy

## Git history

Track source code, manifests, small test fixtures, summary results and figure-generation scripts.

Do not track:

- regenerated large matrices;
- raw benchmark repetitions;
- temporary outputs and logs;
- private or governance-restricted genomic data;
- virtual environments.

## Tagged releases

A manuscript or benchmark release should contain:

- the exact NEXCISION wheel and checksum;
- the benchmarking repository commit;
- frozen manifests and environment files;
- summary results and publication figures;
- optional compressed raw outputs as release assets.

Large frozen datasets should be archived as release assets or in an external research-data repository rather than committed repeatedly to Git history.
