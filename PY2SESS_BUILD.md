# py2sess Build and Test Guide

This guide describes the `py2sess` build and test process used in this
workspace, including the native CPU/CUDA backend used by the RTE-RRTMGP and
pyharp comparison cases.

Primary directory:

```bash
cd /home/chengcli/scix/workspace/PY2ESS/py2sess
```

## Dependencies

Runtime dependencies are declared in `pyproject.toml`:

```text
h5py
numpy
PyYAML
scipy
```

Build and test tools used for local validation:

```text
build
scikit-build-core
setuptools-scm
ruff
```

Optional native backend dependency:

```text
torch
```

The large comparison case also used:

```text
netCDF4
pytest
```

Install the build/test tools if needed:

```bash
python3 -m pip install build scikit-build-core setuptools-scm ruff
```

For the optional native backend, install PyTorch first:

```bash
python3 -m pip install torch
```

If the installed PyTorch package has CUDA support, the native CUDA extension
can be built with the same package. The validated machine used CUDA 13.1
tooling with NVIDIA RTX 5090 GPUs.

## Default CMake Build

The default CMake build prepares the Python package without compiling the optional native backend.

```bash
cmake -S . -B build
cmake --build build
```

Expected output includes:

```text
Preparing py2sess <version> for Python <version>
Built target py2sess_python_sources
```

## Python Package Build

Build the source distribution and wheel:

```bash
python3 -m build
```

Generated artifacts are written to:

```text
dist/
```

Example artifacts:

```text
dist/py2sess-*.tar.gz
dist/py2sess-*.whl
```

If isolated builds cannot reach PyPI, either allow network access or build without isolation after installing the build dependencies:

```bash
python3 -m build --no-isolation
```

## Running Tests From Source

If `py2sess` is not installed into the active Python environment, run tests with `PYTHONPATH=src`:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

In this workspace, the source test suite passed with:

```text
Ran 52 tests
OK
```

When the optional native extension is not built, native-extension tests are skipped.

## Ruff Checks

Run linting:

```bash
python3 -m ruff check .
```

Run format check:

```bash
python3 -m ruff format --check .
```

Expected successful results:

```text
All checks passed!
```

and:

```text
96 files already formatted
```

## Optional Native CPU Backend

The native backend uses PyTorch shared libraries. Configure and build it
separately:

```bash
cmake -S . -B build-native -DPY2SESS_BUILD_NATIVE=ON
cmake --build build-native --parallel 8
```

Expected native artifacts:

```text
build-native/native/libpy2sess_native_core.so
build-native/native/_native.so
```

To validate the native backend without installing into site-packages, add both `src` and the native build output to the import path at runtime:

```bash
PYTHONPATH=src python3 - <<'PY'
from pathlib import Path
import sys
import unittest
import py2sess

py2sess.__path__.append(str(Path("build-native/native").resolve()))

suite = unittest.defaultTestLoader.discover("tests")
result = unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(0 if result.wasSuccessful() else 1)
PY
```

In this workspace, this native-backed test run passed:

```text
Ran 52 tests
OK
```

## Optional Native CUDA Backend

The CUDA backend was built and used in the final large comparison. Build it
separately from the CPU-native build:

```bash
cmake -S . -B build-native-cuda \
  -DPY2SESS_BUILD_NATIVE=ON \
  -DPY2SESS_NATIVE_CUDA=ON
cmake --build build-native-cuda --parallel 8
```

CUDA backend builds require a PyTorch installation with CUDA support and a
compatible CUDA toolkit. For CUDA 13 on the RTX 5090, `native/CMakeLists.txt`
was updated to avoid unsupported `compute_70` code generation and include
modern architectures including `120`.

To make the built extension importable from the source tree for scripts and
tests, copy or install the generated native shared libraries into
`src/py2sess/`:

```bash
cp build-native-cuda/native/_native*.so src/py2sess/
cp build-native-cuda/native/libpy2sess_native*.so src/py2sess/
```

Validate the native extension from the source tree:

```bash
PYTHONPATH=src pytest tests/test_native_backend.py -q
```

Validated result:

```text
6 passed
```

To confirm CUDA support is visible through the Python API:

```bash
CUDA_VISIBLE_DEVICES=1 PYTHONPATH=src python3 - <<'PY'
from py2sess.native import native_backend_info
print(native_backend_info())
PY
```

The validated run reported CUDA support as enabled.

## Running the Comparison Cases

The comparison harness lives at:

```text
/home/chengcli/scix/workspace/PY2ESS/rte_py2sess_comparison
```

The harness can run the py2sess NumPy, Torch CUDA, and native CUDA backends
on the same py2sess-generated optical properties used by RTE-RRTMGP and
pyharp.

Compact case from the workspace root:

```bash
REPEATS=5 WARMUPS=1 PYHARP_NSTR=8 \
  CUDA_VISIBLE_DEVICES=1 ACC_DEVICE_NUM=0 \
  bash rte_py2sess_comparison/run_all.sh
```

Large uploaded case from the workspace root:

```bash
INPUT_ROOT=/home/chengcli/scix/workspace/PY2ESS \
OUTPUT_DIR=outputs_large \
PY2SESS_BACKEND_SET=large-fast \
REPEATS=5 WARMUPS=1 PYHARP_NSTR=8 \
CUDA_VISIBLE_DEVICES=1 ACC_DEVICE_NUM=0 \
  bash rte_py2sess_comparison/run_all.sh
```

The large case used the full UV hyperspectral input with 280,000 wavelength
points and 114 layers. The py2sess outputs are written as raw `.npz` files
for inspection, while compact summary tables are written as CSV and Markdown.

## Notes From This Workspace

- `python3 -m build` succeeded after allowing network access for isolated build requirements.
- `python3 -m pip install -e . --no-build-isolation` built an editable wheel but could not install into `/home/chengcli/pyenv` because that site-packages directory was read-only.
- Source tests were therefore run with `PYTHONPATH=src`.
- The validated native CUDA test command was `PYTHONPATH=src pytest tests/test_native_backend.py -q`.
- Generated build directories and raw solver outputs are intentionally ignored:

```text
build/
build-native/
build-native-cuda/
dist/
rte_py2sess_comparison/outputs*/*.npz
rte_py2sess_comparison/outputs*/*.nc
```
