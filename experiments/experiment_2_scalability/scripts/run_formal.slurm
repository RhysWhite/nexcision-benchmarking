#!/usr/bin/env bash
#SBATCH --job-name=nexc-exp2-formal
#SBATCH --partition=prod
#SBATCH --nodelist=kscprod-bio1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --hint=nomultithread
#SBATCH --exclusive
#SBATCH --mem=0
#SBATCH --time=04:00:00
#SBATCH --output=experiments/experiment_2_scalability/results/formal/slurm-%j.out
#SBATCH --error=experiments/experiment_2_scalability/results/formal/slurm-%j.err

set -euo pipefail
umask 027

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONHASHSEED=0

SUBMIT_ROOT="${SLURM_SUBMIT_DIR:?Submit from the repository root}"
SCRATCH_ROOT="/tmp/${USER}/nexcision-exp2-formal-${SLURM_JOB_ID}"
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

cat > "${SCRATCH_RESULTS}/benchmark_context-${SLURM_JOB_ID}.json" <<EOF
{
  "slurm_job_id": "${SLURM_JOB_ID}",
  "hostname": "$(hostname -f)",
  "allowed_cpu_list": "${ALLOWED_CPUS}",
  "pinned_cpu": "${FIRST_CPU}",
  "exclusive_allocation": true,
  "cache_protocol": "Generated inputs followed by one warm-up per configuration; page cache was not dropped; measured order randomized.",
  "storage_protocol": "Inputs, outputs, virtual environment, and temporary files under node-local /tmp XFS.",
  "timing_scope": "NEXCISION subprocess wall time only; post-run verification and SHA-256 calculation excluded."
}
EOF

"${PIN[@]}" python experiments/experiment_2_scalability/scripts/collect_system_info.py   --output "${SCRATCH_RESULTS}/system_info-start-${SLURM_JOB_ID}.json"

"${PIN[@]}" python experiments/experiment_2_scalability/scripts/run_formal.py   --manifest experiments/experiment_2_scalability/configs/formal_manifest.tsv   --work-dir "${SCRATCH_ROOT}/formal_data"   --measured-results "${SCRATCH_RESULTS}/formal_measured-${SLURM_JOB_ID}.tsv"   --warmup-results "${SCRATCH_RESULTS}/formal_warmups-${SLURM_JOB_ID}.tsv"   --inventory "${SCRATCH_RESULTS}/formal_inventory-${SLURM_JOB_ID}.tsv"   --seed 20260722

"${PIN[@]}" python experiments/experiment_2_scalability/scripts/summarize_formal.py   --results "${SCRATCH_RESULTS}/formal_measured-${SLURM_JOB_ID}.tsv"   --summary-tsv "${SCRATCH_RESULTS}/formal_summary-${SLURM_JOB_ID}.tsv"   --summary-json "${SCRATCH_RESULTS}/formal_summary-${SLURM_JOB_ID}.json"

"${PIN[@]}" python experiments/experiment_2_scalability/scripts/collect_system_info.py   --output "${SCRATCH_RESULTS}/system_info-end-${SLURM_JOB_ID}.json"

sha256sum   "${SCRATCH_RESULTS}/formal_measured-${SLURM_JOB_ID}.tsv"   "${SCRATCH_RESULTS}/formal_warmups-${SLURM_JOB_ID}.tsv"   "${SCRATCH_RESULTS}/formal_inventory-${SLURM_JOB_ID}.tsv"   "${SCRATCH_RESULTS}/formal_summary-${SLURM_JOB_ID}.tsv"   "${SCRATCH_RESULTS}/formal_summary-${SLURM_JOB_ID}.json"   > "${SCRATCH_RESULTS}/formal_SHA256SUMS-${SLURM_JOB_ID}.txt"

printf 'Experiment 2 formal benchmark completed on %s
' "$(hostname -f)"
printf 'CPU affinity: %s (pinned to %s when taskset is available)
' "${ALLOWED_CPUS}" "${FIRST_CPU}"
printf 'Results copied to %s/%s on exit
' "${SUBMIT_ROOT}" "${RESULTS_REL}"
