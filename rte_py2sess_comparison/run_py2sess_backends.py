#!/usr/bin/env python3
"""Run py2sess backends on the exported optical-property case."""

from __future__ import annotations

import argparse
import csv
import importlib
import json
import os
import platform
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import netCDF4
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PY2SESS_ROOT = ROOT / "py2sess"


@dataclass(frozen=True)
class Backend:
    name: str
    backend: str
    device: str
    dtype: str


def _add_py2sess_to_path(py2sess_root: Path) -> None:
    for path in (
        py2sess_root / "src",
        py2sess_root / "build-native" / "native",
        py2sess_root / "build" / "native",
    ):
        if path.exists() and str(path) not in sys.path:
            sys.path.insert(0, str(path))


def _to_numpy(value: Any) -> np.ndarray:
    if hasattr(value, "detach"):
        value = value.detach().cpu().numpy()
    return np.asarray(value, dtype=np.float64)


def _load_case(path: Path) -> dict[str, np.ndarray]:
    with netCDF4.Dataset(path) as ds:
        return {
            "tau": np.asarray(ds["tau_scaled"][:], dtype=np.float64).T,
            "ssa": np.asarray(ds["ssa_scaled"][:], dtype=np.float64).T,
            "g": np.asarray(ds["g_scaled"][:], dtype=np.float64).T,
            "z": np.asarray(ds["z"][:], dtype=np.float64),
            "angles": np.asarray(ds["angles"][:], dtype=np.float64),
            "albedo": np.asarray(ds["albedo"][:], dtype=np.float64),
            "fbeam": np.asarray(ds["fbeam"][:], dtype=np.float64),
        }


def _want_backend(backend_set: str, name: str) -> bool:
    if backend_set == "all":
        return True
    if backend_set == "large-fast":
        return name in {"numpy", "torch_cuda", "native_cuda"}
    if backend_set == "cuda":
        return name in {"torch_cuda", "native_cuda"}
    if backend_set == "cpu":
        return name in {"numpy", "torch_cpu", "native_cpu"}
    return name in {part.strip() for part in backend_set.split(",") if part.strip()}


def _backends(backend_set: str) -> tuple[list[Backend], list[dict[str, str]]]:
    skipped: list[dict[str, str]] = []
    backends = []
    if _want_backend(backend_set, "numpy"):
        backends.append(Backend("numpy", "numpy", "cpu", "float64"))
    try:
        import torch
    except Exception as exc:
        skipped.append({"backend": "torch-cpu", "reason": f"PyTorch unavailable: {exc}"})
        skipped.append({"backend": "torch-cuda", "reason": f"PyTorch unavailable: {exc}"})
        skipped.append({"backend": "native-cpu", "reason": f"PyTorch unavailable: {exc}"})
        skipped.append({"backend": "native-cuda", "reason": f"PyTorch unavailable: {exc}"})
        return backends, skipped

    if _want_backend(backend_set, "torch_cpu"):
        backends.append(Backend("torch_cpu", "torch", "cpu", "float64"))
    if torch.cuda.is_available():
        if _want_backend(backend_set, "torch_cuda"):
            backends.append(Backend("torch_cuda", "torch", "cuda", "float64"))
    elif _want_backend(backend_set, "torch_cuda"):
        skipped.append({"backend": "torch-cuda", "reason": "torch.cuda.is_available() is false"})

    try:
        native = importlib.import_module("py2sess.rtsolver.native_backend")
        supports = native.native_backend_supports_device
        if supports("cpu") and _want_backend(backend_set, "native_cpu"):
            backends.append(Backend("native_cpu", "native", "cpu", "float64"))
        elif _want_backend(backend_set, "native_cpu"):
            skipped.append({"backend": "native-cpu", "reason": "native extension is not built for CPU"})
        if torch.cuda.is_available() and supports("cuda") and _want_backend(backend_set, "native_cuda"):
            backends.append(Backend("native_cuda", "native", "cuda", "float64"))
        elif _want_backend(backend_set, "native_cuda"):
            skipped.append({"backend": "native-cuda", "reason": "native extension is not built for CUDA"})
    except Exception as exc:
        skipped.append({"backend": "native-cpu", "reason": f"native backend import failed: {exc}"})
        skipped.append({"backend": "native-cuda", "reason": f"native backend import failed: {exc}"})
    return backends, skipped


def _sync(backend: Backend) -> None:
    if backend.device == "cuda":
        import torch

        torch.cuda.synchronize(torch.device("cuda"))


def _run_once(solver: Any, case: dict[str, np.ndarray], backend: Backend) -> tuple[Any, float]:
    kwargs = dict(
        tau=case["tau"],
        ssa=case["ssa"],
        g=case["g"],
        z=case["z"],
        angles=case["angles"],
        albedo=case["albedo"],
        fbeam=case["fbeam"],
        delta_m_truncation_factor=np.zeros_like(case["tau"]),
    )
    _sync(backend)
    start = time.perf_counter()
    result = solver.forward(**kwargs, include_fo=False)
    _sync(backend)
    return result, time.perf_counter() - start


def _git_sha(path: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(path), "rev-parse", "HEAD"], text=True
        ).strip()
    except Exception:
        return ""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--py2sess-root", type=Path, default=DEFAULT_PY2SESS_ROOT)
    parser.add_argument("--case", type=Path, default=Path("outputs/py2sess_uv_optics.nc"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    parser.add_argument(
        "--backend-set",
        default=os.environ.get("PY2SESS_BACKEND_SET", "all"),
        help="all, large-fast, cpu, cuda, or comma-separated backend names",
    )
    parser.add_argument("--repeats", type=int, default=int(os.environ.get("REPEATS", "5")))
    parser.add_argument("--warmups", type=int, default=int(os.environ.get("WARMUPS", "1")))
    args = parser.parse_args()

    py2sess_root = args.py2sess_root.resolve()
    _add_py2sess_to_path(py2sess_root)

    from py2sess import TwoStreamEss, TwoStreamEssOptions

    case = _load_case(args.case.resolve())
    nrows, nlay = case["tau"].shape
    outdir = args.output_dir.resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    raw_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    backends, skipped = _backends(args.backend_set)
    for backend in backends:
        options = TwoStreamEssOptions(
            nlyr=nlay,
            mode="solar",
            backend=backend.backend,
            torch_device=backend.device,
            torch_dtype=backend.dtype,
            torch_enable_grad=False,
            output_levels=True,
            output_fluxes=True,
            plane_parallel=True,
            delta_scaling=False,
        )
        solver = TwoStreamEss(options)
        last_result = None
        for _ in range(args.warmups):
            last_result, _ = _run_once(solver, case, backend)
        seconds: list[float] = []
        for repeat in range(args.repeats):
            last_result, elapsed = _run_once(solver, case, backend)
            seconds.append(elapsed)
            raw_rows.append(
                {
                    "engine": "py2sess",
                    "backend": backend.name,
                    "device": backend.device,
                    "dtype": backend.dtype,
                    "repeat": repeat,
                    "seconds": elapsed,
                    "rows": nrows,
                    "layers": nlay,
                    "rows_per_second": nrows / elapsed,
                    "status": "ok",
                    "skip_reason": "",
                }
            )
        assert last_result is not None
        np.savez(
            outdir / f"py2sess_{backend.name}.npz",
            flux_up=_to_numpy(last_result.flux_up),
            flux_down=_to_numpy(last_result.flux_down),
            flux_net=_to_numpy(last_result.flux_net),
        )
        summary_rows.append(
            {
                "engine": "py2sess",
                "backend": backend.name,
                "device": backend.device,
                "dtype": backend.dtype,
                "repeats": len(seconds),
                "best_s": min(seconds),
                "mean_s": float(np.mean(seconds)),
                "std_s": float(np.std(seconds)),
                "rows_per_second_best": nrows / min(seconds),
                "status": "ok",
                "skip_reason": "",
            }
        )

    for item in skipped:
        row = {
            "engine": "py2sess",
            "backend": item["backend"],
            "device": "",
            "dtype": "",
            "repeats": 0,
            "best_s": "",
            "mean_s": "",
            "std_s": "",
            "rows_per_second_best": "",
            "status": "skipped",
            "skip_reason": item["reason"],
        }
        summary_rows.append(row)

    for path, rows in (
        (outdir / "py2sess_timings_raw.csv", raw_rows),
        (outdir / "py2sess_timings_summary.csv", summary_rows),
    ):
        if rows:
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)

    env = {
        "python": sys.version,
        "platform": platform.platform(),
        "py2sess_root": str(py2sess_root),
        "py2sess_git_sha": _git_sha(py2sess_root),
    }
    try:
        import torch

        env["torch"] = torch.__version__
        env["torch_cuda_available"] = bool(torch.cuda.is_available())
        env["torch_cuda_device"] = (
            torch.cuda.get_device_name(0) if torch.cuda.is_available() else ""
        )
    except Exception as exc:
        env["torch_error"] = str(exc)
    (outdir / "environment_py2sess.json").write_text(
        json.dumps(env, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote py2sess results in {outdir}")


if __name__ == "__main__":
    main()
