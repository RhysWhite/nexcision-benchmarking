#!/usr/bin/env bash
#SBATCH --job-name=nexc-exp2-pilot
#SBATCH --partition=prod
#SBATCH --nodelist=kscprod-bio1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --hint=nomultithread
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --output=experiments/experiment_2_scalability/results/pilot/slurm-%j.out
#SBATCH --error=experiments/experiment_2_scalability/results/pilot/slurm-%j.err

set -euo pipefail

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONHASHSEED=0

SUBMIT_ROOT="${SLURM_SUBMIT_DIR:?Run this script with sbatch from the repository root}"
SCRATCH_ROOT="/tmp/${USER}/nexcision-exp2-${SLURM_JOB_ID}"
SCRATCH_REPO="${SCRATCH_ROOT}/repo"
RESULTS_REL="experiments/experiment_2_scalability/results/pilot"

mkdir -p "${SCRATCH_REPO}" "${SUBMIT_ROOT}/${RESULTS_REL}"
trap 'rm -rf "${SCRATCH_ROOT}"' EXIT

cp -a "${SUBMIT_ROOT}/." "${SCRATCH_REPO}/"
cd "${SCRATCH_REPO}"

python3 -m venv .venv-exp2
source .venv-exp2/bin/activate
python -m pip install --no-deps software/nexcision-0.1.0-py3-none-any.whl

python experiments/experiment_2_scalability/scripts/collect_system_info.py \
  --output "${RESULTS_REL}/system_info-${SLURM_JOB_ID}.json"

python experiments/experiment_2_scalability/scripts/run_pilot.py \
  --manifest experiments/experiment_2_scalability/configs/pilot_manifest.tsv \
  --work-dir "${SCRATCH_ROOT}/pilot_data" \
  --results "${RESULTS_REL}/pilot_results-${SLURM_JOB_ID}.tsv"

cp "${RESULTS_REL}/system_info-${SLURM_JOB_ID}.json" \
   "${SUBMIT_ROOT}/${RESULTS_REL}/"
cp "${RESULTS_REL}/pilot_results-${SLURM_JOB_ID}.tsv" \
   "${SUBMIT_ROOT}/${RESULTS_REL}/"

printf 'Experiment 2 pilot completed on %s\n' "$(hostname -f)"
printf 'Results copied to %s/%s\n' "${SUBMIT_ROOT}" "${RESULTS_REL}"
