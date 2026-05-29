#!/usr/bin/env python3
"""Compare RTE-RRTMGP fluxes with py2sess backend outputs."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import netCDF4
import numpy as np


def _rte_fluxes(path: Path) -> dict[str, np.ndarray]:
    with netCDF4.Dataset(path) as ds:
        return {
            "flux_up": np.asarray(ds["flux_up"][:], dtype=np.float64),
            "flux_down": np.asarray(ds["flux_down"][:], dtype=np.float64),
            "flux_net": np.asarray(ds["flux_net_down_minus_up"][:], dtype=np.float64),
            "flux_down_direct": np.asarray(ds["flux_down_direct"][:], dtype=np.float64),
            "attrs": {
                "best_s": float(getattr(ds, "best_s", np.nan)),
                "mean_s": float(getattr(ds, "mean_s", np.nan)),
                "std_s": float(getattr(ds, "std_s", np.nan)),
                "repeats": int(getattr(ds, "repeats", 0)),
            },
        }


def _metrics(ref: np.ndarray, val: np.ndarray) -> dict[str, float]:
    diff = val - ref
    denom = np.maximum(np.abs(ref), 1.0e-12)
    return {
        "max_abs": float(np.max(np.abs(diff))),
        "max_rel_pct": float(np.max(np.abs(diff) / denom) * 100.0),
        "rmse": float(np.sqrt(np.mean(diff * diff))),
        "ref_sum": float(np.sum(ref)),
        "value_sum": float(np.sum(val)),
        "sum_abs_diff": float(abs(np.sum(val) - np.sum(ref))),
    }


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _timing_summary(outdir: Path, rte_attrs: dict[str, Any]) -> None:
    raw = _read_csv(outdir / "rte_timings.csv")
    raw.extend(_read_csv(outdir / "py2sess_timings_raw.csv"))
    raw.extend(_read_csv(outdir / "pyharp_timings_raw.csv"))
    _write_csv(outdir / "timings_raw.csv", raw)

    rte_raw = _read_csv(outdir / "rte_timings.csv")
    rte_rows_per_second = ""
    if rte_raw:
        rte_rows_per_second = max(float(row["rows_per_second"]) for row in rte_raw)
    rows: list[dict[str, Any]] = [
        {
            "engine": "rte-rrtmgp",
            "backend": "rte-sw",
            "device": "gpu",
            "dtype": "float64",
            "repeats": rte_attrs["repeats"],
            "best_s": rte_attrs["best_s"],
            "mean_s": rte_attrs["mean_s"],
            "std_s": rte_attrs["std_s"],
            "rows_per_second_best": rte_rows_per_second,
            "status": "ok",
            "skip_reason": "",
        }
    ]
    py_rows = _read_csv(outdir / "py2sess_timings_summary.csv")
    rows.extend(py_rows)
    rows.extend(_read_csv(outdir / "pyharp_timings_summary.csv"))
    best = [
        float(row["best_s"])
        for row in rows
        if row.get("status") == "ok" and str(row.get("best_s", "")).strip()
    ]
    baseline = min(best) if best else np.nan
    for row in rows:
        if row.get("status") == "ok" and str(row.get("best_s", "")).strip():
            row["speedup_vs_fastest"] = baseline / float(row["best_s"])
        else:
            row["speedup_vs_fastest"] = ""
    _write_csv(outdir / "timings_summary.csv", rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    parser.add_argument("--rte", type=Path, default=Path("outputs/rte_uv_fluxes.nc"))
    args = parser.parse_args()

    outdir = args.output_dir.resolve()
    rte = _rte_fluxes(args.rte.resolve())
    rows: list[dict[str, Any]] = []
    md_lines = [
        "# py2sess vs RTE-RRTMGP Flux Comparison",
        "",
        "Reference is RTE-RRTMGP RTE shortwave output on py2sess optical properties.",
        "For net flux, py2sess `up - down` is compared against `-(RTE down - up)`.",
        "",
        "| backend | quantity | max abs | max rel (%) | RMSE | sum abs diff |",
        "|---|---:|---:|---:|---:|---:|",
    ]

    for npz_path in sorted([*outdir.glob("py2sess_*.npz"), *outdir.glob("pyharp_*.npz")]):
        backend = npz_path.stem
        if backend.startswith("py2sess_"):
            backend = backend.removeprefix("py2sess_")
        data = np.load(npz_path)
        comparisons = {
            "flux_up": (rte["flux_up"], np.asarray(data["flux_up"], dtype=np.float64)),
            "flux_down": (rte["flux_down"], np.asarray(data["flux_down"], dtype=np.float64)),
            "flux_net_up_minus_down": (
                -rte["flux_net"],
                np.asarray(data["flux_net"], dtype=np.float64),
            ),
        }
        for quantity, (ref, val) in comparisons.items():
            metrics = _metrics(ref, val)
            row = {"backend": backend, "quantity": quantity, **metrics}
            rows.append(row)
            md_lines.append(
                f"| {backend} | {quantity} | {metrics['max_abs']:.6e} | "
                f"{metrics['max_rel_pct']:.6e} | {metrics['rmse']:.6e} | "
                f"{metrics['sum_abs_diff']:.6e} |"
            )

    _write_csv(outdir / "comparison_summary.csv", rows)
    (outdir / "comparison_summary.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    _timing_summary(outdir, rte["attrs"])

    env_parts = {}
    for path in (
        outdir / "environment_case.json",
        outdir / "environment_py2sess.json",
        outdir / "environment_pyharp.json",
    ):
        if path.exists():
            env_parts[path.stem] = json.loads(path.read_text(encoding="utf-8"))
    (outdir / "environment.json").write_text(
        json.dumps(env_parts, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote comparison results in {outdir}")


if __name__ == "__main__":
    main()
