# RTE-RRTMGP GPU Build and Test Summary

This summarizes the GPU build and test process used in this `PY2ESS`
workspace, including the custom RTE driver used to run the RTE shortwave
solver on py2sess optical properties.

## Repository

Primary source directory:

```bash
rte-rrtmgp
```

Build directory:

```bash
rte-rrtmgp/build-gpu
```

## GPU Check

GPU availability was confirmed with:

```bash
nvidia-smi
```

The machine had two NVIDIA GeForce RTX 5090 GPUs visible.

## Python Test Dependency

The CMake test configuration required `dask.array`. It was installed with:

```bash
python3 -m pip install dask
```

## NetCDF-Fortran Compiler Compatibility

The system NetCDF-Fortran installation was built with `gfortran`, so its module file was incompatible with `nvfortran`:

```text
/usr/lib64/gfortran/modules/netcdf.mod
```

To resolve this, NetCDF-Fortran was built locally with `nvfortran` and installed under:

```bash
/tmp/netcdf-fortran-nv
```

The local build used a static NetCDF-Fortran library:

```bash
/tmp/netcdf-fortran-nv/lib/libnetcdff.a
```

and `nvfortran`-compatible module files:

```bash
/tmp/netcdf-fortran-nv/include
```

The comparison driver also links against this same NetCDF-Fortran install.

## CMake Configure

The GPU build was configured with NVHPC `nvfortran`, OpenACC accelerator kernels, and compute capability 12.0:

```bash
cmake -S rte-rrtmgp -B rte-rrtmgp/build-gpu \
  -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  -DRTE_BUILD_TESTING=ON \
  -DRTE_KERNEL_MODE=accel \
  -DCMAKE_Fortran_COMPILER=nvfortran \
  -DCMAKE_Fortran_FLAGS='-O3 -fast -Minfo=accel -Mallocatable=03 -Mpreprocess -acc=gpu -gpu=cc120' \
  -DNetCDF_Fortran_LIBRARY=/tmp/netcdf-fortran-nv/lib/libnetcdff.a \
  -DNetCDF_Fortran_INCLUDE_DIR=/tmp/netcdf-fortran-nv/include \
  -DCMAKE_EXE_LINKER_FLAGS=/usr/lib64/libnetcdf.so
```

## Build

The full project was built with:

```bash
cmake --build rte-rrtmgp/build-gpu --parallel 8
```

Key build artifacts:

```text
rte-rrtmgp/build-gpu/rte/frontend/librte.a
rte-rrtmgp/build-gpu/rrtmgp/frontend/librrtmgp.a
rte-rrtmgp/build-gpu/ssm/libssm.a
```

## GPU Test Run

The OpenACC runtime needed direct GPU device access. Tests were run outside the sandbox and targeted GPU 1:

```bash
CUDA_VISIBLE_DEVICES=1 ACC_DEVICE_NUM=0 ctest --test-dir rte-rrtmgp/build-gpu --output-on-failure -j 2
```

Result:

```text
100% tests passed, 0 tests failed out of 31
Total Test time (real) = 11.62 sec
```

## py2sess Optics Driver Build

The comparison harness builds a small Fortran driver that links against the
RTE libraries and reads py2sess-generated optical properties from NetCDF:

```text
rte_py2sess_comparison/rte_driver/rte_sw_py2sess.F90
```

The driver is configured by `rte_py2sess_comparison/run_all.sh`. The default
paths are:

```text
RTE_BUILD_DIR=/home/chengcli/scix/workspace/PY2ESS/rte-rrtmgp/build-gpu
NETCDF_FORTRAN_PREFIX=/tmp/netcdf-fortran-nv
```

Manual configure command from the workspace root:

```bash
cmake -S rte_py2sess_comparison/rte_driver \
  -B rte_py2sess_comparison/rte_driver/build \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_Fortran_COMPILER=nvfortran \
  -DRTE_BUILD_DIR=/home/chengcli/scix/workspace/PY2ESS/rte-rrtmgp/build-gpu \
  -DNetCDF_Fortran_LIBRARY=/tmp/netcdf-fortran-nv/lib/libnetcdff.a \
  -DNetCDF_Fortran_INCLUDE_DIR=/tmp/netcdf-fortran-nv/include \
  -DCMAKE_EXE_LINKER_FLAGS=/usr/lib64/libnetcdf.so
```

Build command:

```bash
cmake --build rte_py2sess_comparison/rte_driver/build --parallel 8
```

Generated executable:

```text
rte_py2sess_comparison/rte_driver/build/rte_sw_py2sess
```

## Running RTE-RRTMGP on py2sess Optical Properties

The driver does not call RRTMGP gas optics. Instead, py2sess prepares
delta-M-scaled optical tensors (`tau`, `ssa`, and `g`) and writes them to a
canonical NetCDF file. The RTE shortwave solver then consumes those tensors
directly. This is the reverse-way comparison requested for the test cases:
RTE-RRTMGP solver, py2sess optical properties.

Compact case:

```bash
REPEATS=5 WARMUPS=1 PYHARP_NSTR=8 \
  CUDA_VISIBLE_DEVICES=1 ACC_DEVICE_NUM=0 \
  bash rte_py2sess_comparison/run_all.sh
```

Large uploaded case:

```bash
INPUT_ROOT=/home/chengcli/scix/workspace/PY2ESS \
OUTPUT_DIR=outputs_large \
PY2SESS_BACKEND_SET=large-fast \
REPEATS=5 WARMUPS=1 PYHARP_NSTR=8 \
CUDA_VISIBLE_DEVICES=1 ACC_DEVICE_NUM=0 \
  bash rte_py2sess_comparison/run_all.sh
```

The large case completed successfully on GPU 1 and produced:

```text
rte_py2sess_comparison/outputs_large/rte_uv_fluxes.nc
rte_py2sess_comparison/outputs_large/rte_timings.csv
rte_py2sess_comparison/outputs_large/comparison_vs_pyharp_disort8.csv
rte_py2sess_comparison/outputs_large/comparison_vs_pyharp_disort8.md
```

## Notes

- `RTE_KERNEL_MODE=accel` selects the accelerator kernel implementations.
- `-acc=gpu -gpu=cc120` builds OpenACC GPU code for the RTX 5090 architecture.
- The test suite fetches `rrtmgp-data` during CTest if it is not already present.
- `rte-rrtmgp/build-gpu/` is generated build output and is currently untracked.
- `rte_py2sess_comparison/rte_driver/build/` is generated build output and is ignored.
- Raw comparison `.nc` and `.npz` outputs are ignored; summary CSV/Markdown
  tables are tracked.
