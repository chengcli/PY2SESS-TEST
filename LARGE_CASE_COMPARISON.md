# Large Full-Spectrum UV Comparison

This note records how the large uploaded py2sess case was built, run, and
validated against pydisort DISORT 8-stream CPU.

## Repositories And Inputs

- Primary comparison harness: `rte_py2sess_comparison/`
- py2sess source: `py2sess`, git `0a4decef424d6093b7d5fdba0701de758f29f786`
- rte-rrtmgp source: `rte-rrtmgp`, git `ff15f7c99d560e2ee24e1f2e0cdf55477ab79c95`
- pyharp source consulted: `/home/chengcli/scix/repos/pyharp`, git `774512f95d573334f22eb0942a843af702334c35`
- Installed pyharp package: `2.4.6`
- Torch: `2.10.0+cu128`

Uploaded large input layout:

```text
benchmark_bundles/
  uv_scene_python.yaml
  uv_gas_xsec.nc
  uv_reference_outputs.npz
profiles/
  Profiles_1_2006726_1500.dat
geocape_data/
  ...
```

The comparison used the large UV solar full-spectrum case:

- wavelengths: `280000`
- layers: `114`
- mode: `solar`
- `mu0`: `0.6729866834669562`
- py2sess optical-property preparation time: `2.0166 s`
- py2sess optical preprocessing time: `0.9249 s`

## Build Steps

### RTE-RRTMGP GPU Build

The comparison driver links against the existing GPU-enabled RTE-RRTMGP build:

```bash
RTE_BUILD_DIR=/home/chengcli/scix/workspace/PY2ESS/rte-rrtmgp/build-gpu
NETCDF_FORTRAN_PREFIX=/tmp/netcdf-fortran-nv
```

The driver is built automatically by:

```bash
cmake -S rte_py2sess_comparison/rte_driver \
  -B rte_py2sess_comparison/rte_driver/build \
  -DCMAKE_Fortran_COMPILER=nvfortran \
  -DRTE_BUILD_DIR=/home/chengcli/scix/workspace/PY2ESS/rte-rrtmgp/build-gpu \
  -DNETCDF_FORTRAN_PREFIX=/tmp/netcdf-fortran-nv

cmake --build rte_py2sess_comparison/rte_driver/build -j
```

### py2sess Native CPU/CUDA Build

The native py2sess extension was built and installed into the local source
package so `PYTHONPATH=py2sess/src` can import `py2sess._native` and
`py2sess._native_cuda`.

```bash
TORCH_CUDA_ARCH_LIST=12.0 cmake -S py2sess -B py2sess/build-native-cuda \
  -DPY2SESS_BUILD_NATIVE=ON \
  -DPY2SESS_NATIVE_CUDA=ON \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CUDA_ARCHITECTURES=120 \
  -DCMAKE_INSTALL_PREFIX=/home/chengcli/scix/workspace/PY2ESS/py2sess/src

TORCH_CUDA_ARCH_LIST=12.0 cmake --build py2sess/build-native-cuda -j
cmake --install py2sess/build-native-cuda
```

One local build fix was needed in `py2sess/native/CMakeLists.txt`: CUDA 13 no
longer supports `compute_70`, so the default native CUDA architecture list now
drops `70` for CUDA 13+ and includes `120` for the RTX 5090.

Native tests:

```bash
cd py2sess
PYTHONPATH=src pytest tests/test_native_backend.py -q
```

Result:

```text
6 passed
```

## Test Command

The large comparison was run from the workspace root:

```bash
INPUT_ROOT=/home/chengcli/scix/workspace/PY2ESS \
OUTPUT_DIR=outputs_large \
PY2SESS_BACKEND_SET=large-fast \
REPEATS=5 \
WARMUPS=1 \
PYHARP_NSTR=8 \
CUDA_VISIBLE_DEVICES=1 \
ACC_DEVICE_NUM=0 \
bash rte_py2sess_comparison/run_all.sh
```

`PY2SESS_BACKEND_SET=large-fast` runs py2sess NumPy CPU, Torch CUDA, and native
CUDA. py2sess Torch CPU and native CPU were skipped for the large run because
the compact-case Torch CPU timing extrapolates to a long CPU-only run and does
not affect the GPU comparison.

Outputs were written to:

```text
rte_py2sess_comparison/outputs_large/
```

Key report files:

```text
comparison_vs_pyharp_disort8.md
timings_summary.csv
environment.json
```

## Results

Accuracy reference: pydisort DISORT 8-stream CPU.

Relative max errors are very large for some rows because the reference contains
near-zero level fluxes. RMSE and max absolute error are the useful metrics for
this case.

| Solver | Flux up RMSE | Flux down RMSE | Net flux RMSE | Best time |
|---|---:|---:|---:|---:|
| pydisort DISORT 8-stream CPU | `0.000000e+00` | `0.000000e+00` | `0.000000e+00` | `8.335687 s` |
| RTE-RRTMGP SW GPU | `1.765728e-04` | `4.763478e-05` | `1.807282e-04` | `0.271440 s` |
| pyharp Toon CPU | `1.011729e-04` | `2.698480e-05` | `1.022342e-04` | `0.241773 s` |
| pyharp Toon CUDA | `1.011729e-04` | `2.698480e-05` | `1.022342e-04` | `0.099100 s` |
| py2sess NumPy CPU | `3.285478e-03` | `2.654977e-05` | `3.277981e-03` | `8.248388 s` |
| py2sess Torch CUDA | `3.286123e-03` | `2.654977e-05` | `3.278627e-03` | `0.359065 s` |
| py2sess native CUDA | `3.286123e-03` | `2.654977e-05` | `3.278627e-03` | `0.323266 s` |

Timing details:

| Engine | Backend | Device | Best time | Mean time | Rows/s best |
|---|---|---|---:|---:|---:|
| RTE-RRTMGP | RTE SW | GPU | `0.271440 s` | `0.272292 s` | `1,031,535.51` |
| pyharp | Toon CUDA | CUDA | `0.099100 s` | `0.099233 s` | `2,825,423.33` |
| pyharp | Toon CPU | CPU | `0.241773 s` | `0.258403 s` | `1,158,110.43` |
| py2sess | native CUDA | CUDA | `0.323266 s` | `0.323948 s` | `866,159.23` |
| py2sess | Torch CUDA | CUDA | `0.359065 s` | `0.359325 s` | `779,803.10` |
| py2sess | NumPy CPU | CPU | `8.248388 s` | `8.417679 s` | `33,946.03` |
| pydisort | DISORT 8-stream CPU | CPU | `8.335687 s` | `8.416888 s` | `33,590.51` |

## Validation Summary

- The large py2sess UV scene loaded successfully and generated a
  `280000 x 114` optical tensor case.
- RTE-RRTMGP consumed the py2sess optical properties directly through the
  RTE shortwave solver.
- pyharp Toon ran on both CPU and CUDA.
- pydisort DISORT 8-stream CPU ran and was used as the zero-error reference.
- py2sess NumPy CPU, Torch CUDA, and native CUDA completed.
- Final comparison command completed successfully and wrote all reports under
  `rte_py2sess_comparison/outputs_large/`.

