#!/usr/bin/env python3
"""Compare all solver outputs against pyharp DISORT as the reference."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

import netCDF4
import numpy as np


def _metrics(ref: np.ndarray, val: np.ndarray) -> dict[str, float]:
    diff = val - ref
    denom = np.maximum(np.abs(ref), 1.0e-12)
    return {
        "max_abs": float(np.max(np.abs(diff))),
        "max_rel_pct": float(np.max(np.abs(diff) / denom) * 100.0),
        "rmse": float(np.sqrt(np.mean(diff * diff))),
        "sum_abs_diff": float(abs(np.sum(val) - np.sum(ref))),
    }


def _load_npz(path: Path) -> dict[str, np.ndarray]:
    data = np.load(path)
    return {
        "flux_up": np.asarray(data["flux_up"], dtype=np.float64),
        "flux_down": np.asarray(data["flux_down"], dtype=np.float64),
        "flux_net": np.asarray(data["flux_net"], dtype=np.float64),
    }


def _load_rte(path: Path) -> dict[str, np.ndarray]:
    with netCDF4.Dataset(path) as ds:
        up = np.asarray(ds["flux_up"][:], dtype=np.float64)
        down = np.asarray(ds["flux_down"][:], dtype=np.float64)
    return {
        "flux_up": up,
        "flux_down": down,
        "flux_net": up - down,
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
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    parser.add_argument(
        "--reference",
        type=Path,
        default=Path("outputs/pyharp_disort_cpu.npz"),
        help="pyharp DISORT reference NPZ, expected to be generated with --nstr 8.",
    )
    parser.add_argument("--rte", type=Path, default=Path("outputs/rte_uv_fluxes.nc"))
    args = parser.parse_args()

    outdir = args.output_dir.resolve()
    ref = _load_npz(args.reference.resolve())
    candidates: list[tuple[str, dict[str, np.ndarray]]] = [
        ("pydisort_disort_8stream_cpu", ref)
    ]
    if args.rte.exists():
        candidates.append(("rte_rrtmgp_sw_gpu", _load_rte(args.rte.resolve())))
    for path in sorted(outdir.glob("py2sess_*.npz")):
        candidates.append((path.stem, _load_npz(path)))
    for path in sorted(outdir.glob("pyharp_*.npz")):
        if path.resolve() == args.reference.resolve():
            continue
        candidates.append((path.stem, _load_npz(path)))

    rows: list[dict[str, Any]] = []
    md = [
        "# Solver Accuracy vs pyharp DISORT 8-Stream",
        "",
        "Reference: `pyharp_disort_cpu.npz`, generated with `--nstr 8`.",
        "",
        "| solver | quantity | max abs | max rel (%) | RMSE | sum abs diff |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for solver, values in candidates:
        for quantity in ("flux_up", "flux_down", "flux_net"):
            metrics = _metrics(ref[quantity], values[quantity])
            row = {"solver": solver, "quantity": quantity, **metrics}
            rows.append(row)
            md.append(
                f"| {solver} | {quantity} | {metrics['max_abs']:.6e} | "
                f"{metrics['max_rel_pct']:.6e} | {metrics['rmse']:.6e} | "
                f"{metrics['sum_abs_diff']:.6e} |"
            )

    _write_csv(outdir / "comparison_vs_pyharp_disort8.csv", rows)
    (outdir / "comparison_vs_pyharp_disort8.md").write_text(
        "\n".join(md) + "\n", encoding="utf-8"
    )
    print(f"wrote {outdir / 'comparison_vs_pyharp_disort8.md'}")


if __name__ == "__main__":
    main()
