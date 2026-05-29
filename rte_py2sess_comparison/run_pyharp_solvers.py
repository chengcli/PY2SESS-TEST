#!/usr/bin/env python3
"""Run pyharp Toon and DISORT solvers on the exported py2sess optical case."""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import netCDF4
import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PYHARP_SOURCE_ROOT = Path("/home/chengcli/scix/repos/pyharp")


def _load_case(path: Path) -> dict[str, np.ndarray]:
    with netCDF4.Dataset(path) as ds:
        return {
            "tau": np.asarray(ds["tau_scaled"][:], dtype=np.float64).T,
            "ssa": np.asarray(ds["ssa_scaled"][:], dtype=np.float64).T,
            "g": np.asarray(ds["g_scaled"][:], dtype=np.float64).T,
            "albedo": np.asarray(ds["albedo"][:], dtype=np.float64),
            "fbeam": np.asarray(ds["fbeam"][:], dtype=np.float64),
            "mu0": float(np.asarray(ds["mu0"][:], dtype=np.float64)),
            "wavenumber": np.asarray(ds["wavenumber_cm_inv"][:], dtype=np.float64),
        }


def _git_sha(path: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(path), "rev-parse", "HEAD"], text=True
        ).strip()
    except Exception:
        return ""


def _wave_bounds(wavenumber: np.ndarray) -> tuple[list[float], list[float]]:
    wn = np.asarray(wavenumber, dtype=np.float64)
    if wn.size == 1:
        return [float(max(wn[0] - 0.5, 0.0))], [float(wn[0] + 0.5)]
    edges = np.empty(wn.size + 1, dtype=np.float64)
    edges[1:-1] = 0.5 * (wn[:-1] + wn[1:])
    edges[0] = wn[0] - 0.5 * (wn[1] - wn[0])
    edges[-1] = wn[-1] + 0.5 * (wn[-1] - wn[-2])
    lo = np.minimum(edges[:-1], edges[1:])
    hi = np.maximum(edges[:-1], edges[1:])
    lo = np.maximum(lo, 0.0)
    return lo.tolist(), hi.tolist()


def _prepare_tensors(
    case: dict[str, np.ndarray],
    *,
    nstr: int,
    device: torch.device,
) -> tuple[torch.Tensor, torch.Tensor, dict[str, torch.Tensor], list[float], list[float]]:
    tau = case["tau"][:, ::-1].copy()
    ssa = case["ssa"][:, ::-1].copy()
    g = case["g"][:, ::-1].copy()
    nrow, nlay = tau.shape

    prop = torch.zeros((nrow, 1, nlay, 2 + nstr), dtype=torch.float64, device=device)
    prop[:, 0, :, 0] = torch.as_tensor(tau, dtype=torch.float64, device=device)
    prop[:, 0, :, 1] = torch.as_tensor(ssa, dtype=torch.float64, device=device)
    g_t = torch.as_tensor(g, dtype=torch.float64, device=device)
    for moment in range(nstr):
        prop[:, 0, :, 2 + moment] = g_t ** (moment + 1)

    bc = {
        "fbeam": torch.as_tensor(case["fbeam"][:, None], dtype=torch.float64, device=device),
        "umu0": torch.as_tensor([case["mu0"]], dtype=torch.float64, device=device),
        "albedo": torch.as_tensor(case["albedo"][:, None], dtype=torch.float64, device=device),
    }
    wave_lo, wave_hi = _wave_bounds(case["wavenumber"])
    return prop, prop[..., :3].contiguous(), bc, wave_lo, wave_hi


def _sync(device: torch.device) -> None:
    if device.type == "cuda":
        torch.cuda.synchronize(device)


def _to_flux_np(result: torch.Tensor) -> dict[str, np.ndarray]:
    arr = result.detach().cpu().numpy()
    # pyharp levels are surface-to-TOA. Convert back to TOA-to-surface.
    arr = arr[:, 0, ::-1, :]
    flux_up = np.asarray(arr[:, :, 0], dtype=np.float64)
    flux_down = np.asarray(arr[:, :, 1], dtype=np.float64)
    return {
        "flux_up": flux_up,
        "flux_down": flux_down,
        "flux_net": flux_up - flux_down,
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", type=Path, default=Path("outputs/py2sess_uv_optics.nc"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    parser.add_argument("--pyharp-source-root", type=Path, default=DEFAULT_PYHARP_SOURCE_ROOT)
    parser.add_argument("--nstr", type=int, default=4)
    parser.add_argument("--repeats", type=int, default=int(os.environ.get("REPEATS", "5")))
    parser.add_argument("--warmups", type=int, default=int(os.environ.get("WARMUPS", "1")))
    args = parser.parse_args()

    import pyharp
    import pydisort

    case = _load_case(args.case.resolve())
    outdir = args.output_dir.resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    nrow, nlay = case["tau"].shape
    device = torch.device("cpu")
    prop_disort, prop_toon, bc, wave_lo, wave_hi = _prepare_tensors(
        case, nstr=args.nstr, device=device
    )

    toon_opt = pyharp.ToonMcKay89Options()
    toon_opt.wave_lower(wave_lo)
    toon_opt.wave_upper(wave_hi)
    toon = pyharp.ToonMcKay89(toon_opt)

    disort_opt = pydisort.DisortOptions()
    disort_opt.upward(True)
    disort_opt.flags("lamber,quiet,onlyfl")
    disort_opt.wave_lower(wave_lo)
    disort_opt.wave_upper(wave_hi)
    pyharp.disort_config(disort_opt, args.nstr, nlay, 1, nrow)
    disort = pydisort.Disort(disort_opt)

    solvers = [
        ("pyharp_toon_cpu", "pyharp", "toon_cpu", toon, prop_toon, bc, device),
        (
            "pyharp_disort_cpu",
            "pydisort",
            f"disort_{args.nstr}stream_cpu",
            disort,
            prop_disort,
            bc,
            device,
        ),
    ]
    if torch.cuda.is_available():
        cuda_device = torch.device("cuda")
        _, prop_toon_cuda, bc_cuda, _, _ = _prepare_tensors(
            case, nstr=args.nstr, device=cuda_device
        )
        toon_cuda_opt = pyharp.ToonMcKay89Options()
        toon_cuda_opt.wave_lower(wave_lo)
        toon_cuda_opt.wave_upper(wave_hi)
        toon_cuda = pyharp.ToonMcKay89(toon_cuda_opt)
        solvers.append(
            (
                "pyharp_toon_cuda",
                "pyharp",
                "toon_cuda",
                toon_cuda,
                prop_toon_cuda,
                bc_cuda,
                cuda_device,
            )
        )
    raw_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    for label, engine_name, solver_name, solver, prop, solver_bc, solver_device in solvers:
        result = None
        for _ in range(args.warmups):
            result = solver(prop, **solver_bc)
        seconds: list[float] = []
        for repeat in range(args.repeats):
            _sync(solver_device)
            start = time.perf_counter()
            result = solver(prop, **solver_bc)
            _sync(solver_device)
            elapsed = time.perf_counter() - start
            seconds.append(elapsed)
            raw_rows.append(
                {
                    "engine": engine_name,
                    "backend": solver_name,
                    "device": str(solver_device),
                    "dtype": "float64",
                    "repeat": repeat,
                    "seconds": elapsed,
                    "rows": nrow,
                    "layers": nlay,
                    "rows_per_second": nrow / elapsed,
                    "status": "ok",
                    "skip_reason": "",
                }
            )
        assert result is not None
        fluxes = _to_flux_np(result)
        np.savez(outdir / f"{label}.npz", **fluxes)
        summary_rows.append(
            {
                "engine": engine_name,
                "backend": solver_name,
                "device": str(solver_device),
                "dtype": "float64",
                "repeats": len(seconds),
                "best_s": min(seconds),
                "mean_s": float(np.mean(seconds)),
                "std_s": float(np.std(seconds)),
                "rows_per_second_best": nrow / min(seconds),
                "status": "ok",
                "skip_reason": "",
            }
        )

    _write_csv(outdir / "pyharp_timings_raw.csv", raw_rows)
    _write_csv(outdir / "pyharp_timings_summary.csv", summary_rows)
    env = {
        "python": sys.version,
        "pyharp_package": getattr(pyharp, "__file__", ""),
        "pyharp_version": getattr(pyharp, "__version__", ""),
        "pyharp_source_root": str(args.pyharp_source_root),
        "pyharp_git_sha": _git_sha(args.pyharp_source_root),
        "pydisort_package": getattr(pydisort, "__file__", ""),
        "torch": torch.__version__,
        "torch_cuda_available": bool(torch.cuda.is_available()),
        "nstr": args.nstr,
    }
    (outdir / "environment_pyharp.json").write_text(
        json.dumps(env, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote pyharp results in {outdir}")


if __name__ == "__main__":
    main()
