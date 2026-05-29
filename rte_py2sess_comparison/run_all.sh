#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PY2SESS_ROOT="${PY2SESS_ROOT:-${WORKSPACE_ROOT}/py2sess}"
INPUT_ROOT="${INPUT_ROOT:-}"
RTE_BUILD_DIR="${RTE_BUILD_DIR:-${WORKSPACE_ROOT}/rte-rrtmgp/build-gpu}"
NETCDF_FORTRAN_PREFIX="${NETCDF_FORTRAN_PREFIX:-/tmp/netcdf-fortran-nv}"
REPEATS="${REPEATS:-5}"
WARMUPS="${WARMUPS:-1}"
PYHARP_NSTR="${PYHARP_NSTR:-8}"
OUTPUT_DIR="${OUTPUT_DIR:-outputs}"
PY2SESS_BACKEND_SET="${PY2SESS_BACKEND_SET:-all}"

export RTE_BUILD_DIR
export NETCDF_FORTRAN_PREFIX

cd "${SCRIPT_DIR}"
mkdir -p "${OUTPUT_DIR}" rte_driver/build

prepare_args=(
  --py2sess-root "${PY2SESS_ROOT}"
  --output "${OUTPUT_DIR}/py2sess_uv_optics.nc"
  --metadata "${OUTPUT_DIR}/environment_case.json"
)
if [[ -n "${INPUT_ROOT}" ]]; then
  prepare_args+=(--input-root "${INPUT_ROOT}")
fi

python3 prepare_py2sess_optics.py "${prepare_args[@]}"

cmake -S rte_driver -B rte_driver/build \
  -DCMAKE_Fortran_COMPILER="${FC:-nvfortran}" \
  -DRTE_BUILD_DIR="${RTE_BUILD_DIR}" \
  -DNETCDF_FORTRAN_PREFIX="${NETCDF_FORTRAN_PREFIX}"
cmake --build rte_driver/build -j

./rte_driver/build/rte_sw_py2sess \
  --input "${OUTPUT_DIR}/py2sess_uv_optics.nc" \
  --output "${OUTPUT_DIR}/rte_uv_fluxes.nc" \
  --timing "${OUTPUT_DIR}/rte_timings.csv" \
  --warmups "${WARMUPS}" \
  --repeats "${REPEATS}"

python3 run_py2sess_backends.py \
  --py2sess-root "${PY2SESS_ROOT}" \
  --case "${OUTPUT_DIR}/py2sess_uv_optics.nc" \
  --output-dir "${OUTPUT_DIR}" \
  --backend-set "${PY2SESS_BACKEND_SET}" \
  --warmups "${WARMUPS}" \
  --repeats "${REPEATS}"

python3 run_pyharp_solvers.py \
  --case "${OUTPUT_DIR}/py2sess_uv_optics.nc" \
  --output-dir "${OUTPUT_DIR}" \
  --nstr "${PYHARP_NSTR}" \
  --warmups "${WARMUPS}" \
  --repeats "${REPEATS}"

python3 compare_outputs.py \
  --output-dir "${OUTPUT_DIR}" \
  --rte "${OUTPUT_DIR}/rte_uv_fluxes.nc"

python3 compare_to_pyharp_disort.py \
  --output-dir "${OUTPUT_DIR}" \
  --reference "${OUTPUT_DIR}/pyharp_disort_cpu.npz" \
  --rte "${OUTPUT_DIR}/rte_uv_fluxes.nc"

echo "Wrote ${SCRIPT_DIR}/${OUTPUT_DIR}/comparison_summary.md"
echo "Wrote ${SCRIPT_DIR}/${OUTPUT_DIR}/comparison_vs_pyharp_disort8.md"
echo "Wrote ${SCRIPT_DIR}/${OUTPUT_DIR}/timings_summary.csv"
