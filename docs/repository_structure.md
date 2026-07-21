# Repository organisation

The main NEXCISION repository contains installable software, concise documentation and routine software tests.

This repository contains the larger scientific evaluation:

- **scripts and manifests** are committed;
- **small fixed cases and summary results** are committed;
- **large generated datasets and raw logs** are regenerated or archived externally;
- **manuscript products** are separated from raw experiment output;
- **the exact tested wheel** is retained under `software/`.

This separation keeps installation of NEXCISION lightweight while preserving a complete, auditable experimental record.
