# py2sess Optics Through RTE-RRTMGP

This directory compares py2sess, the RTE shortwave solver from `rte-rrtmgp`,
and pyharp Toon/DISORT solvers on the same py2sess-generated optical
properties.

The workflow uses the checked-in compact hyperspectral-style UV scene:

```text
py2sess/benchmarks/uv_profile1
```

That scene generates 1,000 spectral rows and 114 layers. py2sess also
documents larger UV/TIR full-spectrum bundles, but those external
`benchmark_bundles/` inputs are not present in this workspace.

## What Is Compared

`prepare_py2sess_optics.py` loads the py2sess scene, prepares optical
properties, applies py2sess delta-M scaling once, and writes a canonical
NetCDF case. Both solvers then consume the same scaled `tau`, `ssa`, and `g`
tensors.

The RTE-RRTMGP run uses the RTE shortwave two-stream solver directly. RRTMGP
gas optics are intentionally bypassed so the solver receives the exact
py2sess optical tensors. The pyharp runs use the installed pyharp API and the
source repo at `/home/chengcli/scix/repos/pyharp` is recorded in the
environment manifest.

## Run

From the workspace root:

```bash
bash rte_py2sess_comparison/run_all.sh
```

Useful environment variables:

```bash
RTE_BUILD_DIR=/path/to/rte-rrtmgp/build-gpu
NETCDF_FORTRAN_PREFIX=/path/to/netcdf-fortran
PY2SESS_ROOT=/path/to/py2sess
REPEATS=5
WARMUPS=1
PYHARP_NSTR=8
```

Defaults are chosen for this workspace:

```text
RTE_BUILD_DIR=../rte-rrtmgp/build-gpu, resolved from rte_driver/build
NETCDF_FORTRAN_PREFIX=/tmp/netcdf-fortran-nv
PY2SESS_ROOT=../py2sess, resolved from this directory
```

## Outputs

Files are written under `rte_py2sess_comparison/outputs/`:

```text
py2sess_uv_optics.nc
rte_uv_fluxes.nc
py2sess_<backend>.npz
pyharp_toon_cpu.npz
pyharp_disort_cpu.npz
timings_raw.csv
timings_summary.csv
comparison_summary.csv
comparison_summary.md
comparison_vs_pyharp_disort8.csv
comparison_vs_pyharp_disort8.md
environment.json
```

Flux sign convention is handled in the comparison. py2sess reports net flux
as `up - down`; RTE reports net flux as `down - up`.
