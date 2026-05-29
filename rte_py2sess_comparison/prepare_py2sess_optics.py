#!/usr/bin/env python3
"""Export py2sess optical properties for an RTE-RRTMGP solver run."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import netCDF4
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PY2SESS_ROOT = ROOT / "py2sess"


def _add_py2sess_to_path(py2sess_root: Path) -> None:
    src = py2sess_root / "src"
    examples = py2sess_root / "examples"
    for path in (src, examples):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))


def _write_var(ds: netCDF4.Dataset, name: str, dims: tuple[str, ...], data: np.ndarray) -> None:
    var = ds.createVariable(name, "f8", dims)
    var[:] = data


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--py2sess-root", type=Path, default=DEFAULT_PY2SESS_ROOT)
    parser.add_argument("--input-root", type=Path, default=None)
    parser.add_argument("--case", choices=["uv"], default="uv")
    parser.add_argument("--output", type=Path, default=Path("outputs/py2sess_uv_optics.nc"))
    parser.add_argument("--metadata", type=Path, default=Path("outputs/environment_case.json"))
    args = parser.parse_args()

    py2sess_root = args.py2sess_root.resolve()
    _add_py2sess_to_path(py2sess_root)

    from py2sess.optical.delta_m import delta_m_scale_optical_properties
    from py2sess.scene import load_scene

    if args.input_root is None:
        case_dir = py2sess_root / "benchmarks" / "uv_profile1"
        profile = case_dir / "profile.csv"
        config = case_dir / "scene.yaml"
        source_scene = str(case_dir)
        case_name = "uv_profile1"
    else:
        input_root = args.input_root.resolve()
        profile = input_root / "profiles" / "Profiles_1_2006726_1500.dat"
        config = input_root / "benchmark_bundles" / "uv_scene_python.yaml"
        source_scene = str(input_root)
        case_name = "uv_full_spectrum"
    scene = load_scene(
        profile=profile,
        config=config,
        strict_runtime_inputs=True,
    )
    inputs = scene.to_forward_inputs()
    kwargs = inputs.kwargs

    tau = np.asarray(kwargs["tau"], dtype=np.float64)
    ssa = np.asarray(kwargs["ssa"], dtype=np.float64)
    g = np.asarray(kwargs["g"], dtype=np.float64)
    scaling = np.asarray(kwargs["delta_m_truncation_factor"], dtype=np.float64)
    tau_scaled, ssa_scaled, g_scaled = delta_m_scale_optical_properties(tau, ssa, g, scaling)

    angles = np.asarray(kwargs["angles"], dtype=np.float64)
    mu0 = math.cos(math.radians(float(angles[0])))
    if mu0 <= 0.0:
        raise ValueError(f"solar zenith angle gives non-positive mu0: {angles[0]}")

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    n_spectral, n_layer = tau.shape
    n_level = n_layer + 1

    wavelengths = np.asarray(inputs.wavelengths, dtype=np.float64)
    if wavelengths.shape != (n_spectral,):
        wavelengths = np.arange(1, n_spectral + 1, dtype=np.float64)
    wavenumber = 1.0e7 / wavelengths

    with netCDF4.Dataset(output, "w") as ds:
        ds.setncattr("case", case_name)
        ds.setncattr("mode", "solar")
        ds.setncattr("description", "py2sess UV optical properties with delta-M scaling pre-applied")
        ds.createDimension("layer", n_layer)
        ds.createDimension("level", n_level)
        ds.createDimension("spectral", n_spectral)
        ds.createDimension("angle", 3)
        _write_var(ds, "tau_scaled", ("layer", "spectral"), tau_scaled.T)
        _write_var(ds, "ssa_scaled", ("layer", "spectral"), ssa_scaled.T)
        _write_var(ds, "g_scaled", ("layer", "spectral"), g_scaled.T)
        _write_var(ds, "tau_raw", ("layer", "spectral"), tau.T)
        _write_var(ds, "ssa_raw", ("layer", "spectral"), ssa.T)
        _write_var(ds, "g_raw", ("layer", "spectral"), g.T)
        _write_var(ds, "delta_m_truncation_factor", ("layer", "spectral"), scaling.T)
        _write_var(ds, "z", ("level",), np.asarray(kwargs["z"], dtype=np.float64))
        _write_var(ds, "angles", ("angle",), angles)
        _write_var(ds, "mu0", (), np.asarray(mu0, dtype=np.float64))
        _write_var(ds, "albedo", ("spectral",), np.asarray(kwargs["albedo"], dtype=np.float64))
        _write_var(ds, "fbeam", ("spectral",), np.asarray(kwargs["fbeam"], dtype=np.float64))
        _write_var(ds, "wavelength_nm", ("spectral",), wavelengths)
        _write_var(ds, "wavenumber_cm_inv", ("spectral",), wavenumber)

    args.metadata.resolve().parent.mkdir(parents=True, exist_ok=True)
    args.metadata.resolve().write_text(
        json.dumps(
            {
                "case": case_name,
                "mode": inputs.mode,
                "wavelengths": int(n_spectral),
                "layers": int(n_layer),
                "mu0": float(mu0),
                "scene_timings": {key: float(value) for key, value in inputs.timings.items()},
                "source_scene": source_scene,
                "output": str(output),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
