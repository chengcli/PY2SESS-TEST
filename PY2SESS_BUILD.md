# py2sess Build Guide

This guide describes how to build and test `py2sess` in this workspace.

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

Install the build/test tools if needed:

```bash
python3 -m pip install build scikit-build-core setuptools-scm ruff
```

For the optional native backend, install PyTorch first:

```bash
python3 -m pip install torch
```

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

The native backend uses PyTorch shared libraries. Configure and build it separately:

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

The CMake option exists but was not used in the completed validation:

```bash
cmake -S . -B build-native-cuda \
  -DPY2SESS_BUILD_NATIVE=ON \
  -DPY2SESS_NATIVE_CUDA=ON
cmake --build build-native-cuda --parallel 8
```

CUDA backend builds require a PyTorch installation with CUDA support and a compatible CUDA toolkit.

## Notes From This Workspace

- `python3 -m build` succeeded after allowing network access for isolated build requirements.
- `python3 -m pip install -e . --no-build-isolation` built an editable wheel but could not install into `/home/chengcli/pyenv` because that site-packages directory was read-only.
- Source tests were therefore run with `PYTHONPATH=src`.
- Generated build directories are untracked:

```text
build/
build-native/
dist/
```
