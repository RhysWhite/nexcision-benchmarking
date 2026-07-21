#!/usr/bin/env bash
#SBATCH --job-name=nexc-exp2-smoke
#SBATCH --partition=prod
#SBATCH --nodelist=kscprod-bio1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --hint=nomultithread
#SBATCH --mem=16G
#SBATCH --time=00:15:00
#SBATCH --output=experiments/experiment_2_scalability/results/formal/slurm-smoke-%j.out
#SBATCH --error=experiments/experiment_2_scalability/results/formal/slurm-smoke-%j.err

set -euo pipefail
umask 027

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONHASHSEED=0

SUBMIT_ROOT="${SLURM_SUBMIT_DIR:?Submit from the repository root}"
SCRATCH_ROOT="/tmp/${USER}/nexcision-exp2-smoke-${SLURM_JOB_ID}"
SCRATCH_REPO="${SCRATCH_ROOT}/repo"
SCRATCH_RESULTS="${SCRATCH_ROOT}/results"
RESULTS_REL="experiments/experiment_2_scalability/results/formal"

copy_back_and_clean() {
    status=$?
    set +e
    mkdir -p "${SUBMIT_ROOT}/${RESULTS_REL}"
    if [[ -d "${SCRATCH_RESULTS}" ]]; then
        cp -a "${SCRATCH_RESULTS}/." "${SUBMIT_ROOT}/${RESULTS_REL}/"
    fi
    rm -rf "${SCRATCH_ROOT}"
    exit "${status}"
}
trap copy_back_and_clean EXIT

mkdir -p "${SCRATCH_REPO}" "${SCRATCH_ROOT}/tmp" "${SCRATCH_RESULTS}" "${SUBMIT_ROOT}/${RESULTS_REL}"
cp -a "${SUBMIT_ROOT}/." "${SCRATCH_REPO}/"
cd "${SCRATCH_REPO}"
export TMPDIR="${SCRATCH_ROOT}/tmp"

python3 -m venv .venv-exp2
source .venv-exp2/bin/activate
python -m pip install --no-deps software/nexcision-0.1.0-py3-none-any.whl

ALLOWED_CPUS=$(awk '/Cpus_allowed_list/ {print $2}' /proc/self/status)
FIRST_CPU=$(printf '%s' "${ALLOWED_CPUS}" | cut -d',' -f1 | cut -d'-' -f1)
if command -v taskset >/dev/null 2>&1; then
    PIN=(taskset -c "${FIRST_CPU}")
else
    PIN=()
fi

"${PIN[@]}" python experiments/experiment_2_scalability/scripts/run_formal.py   --manifest experiments/experiment_2_scalability/configs/formal_smoke_manifest.tsv   --work-dir "${SCRATCH_ROOT}/formal_smoke_data"   --measured-results "${SCRATCH_RESULTS}/smoke_measured-${SLURM_JOB_ID}.tsv"   --warmup-results "${SCRATCH_RESULTS}/smoke_warmups-${SLURM_JOB_ID}.tsv"   --inventory "${SCRATCH_RESULTS}/smoke_inventory-${SLURM_JOB_ID}.tsv"

"${PIN[@]}" python experiments/experiment_2_scalability/scripts/summarize_formal.py   --results "${SCRATCH_RESULTS}/smoke_measured-${SLURM_JOB_ID}.tsv"   --summary-tsv "${SCRATCH_RESULTS}/smoke_summary-${SLURM_JOB_ID}.tsv"   --summary-json "${SCRATCH_RESULTS}/smoke_summary-${SLURM_JOB_ID}.json"

printf 'Experiment 2 formal-runner smoke test completed on %s
' "$(hostname -f)"
printf 'CPU affinity: %s (pinned to %s when taskset is available)
' "${ALLOWED_CPUS}" "${FIRST_CPU}"
